#!/usr/bin/env python3
"""Inspect or extract an Android logical partition from sparse/raw super."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from pathlib import Path
import stat
import struct


SPARSE_MAGIC = 0xED26FF3A
GEOMETRY_MAGIC = 0x616C4467
METADATA_MAGIC = 0x414C5030
SECTOR = 512


class ImageReader:
    def __init__(self, path: Path):
        self.path = path
        self.stream = path.open("rb", buffering=0)
        first = self.stream.read(28)
        self.stream.seek(0)
        self.spans: list[tuple[int, int, int, int]] | None = None
        self.starts: list[int] = []
        if len(first) >= 28 and struct.unpack_from("<I", first)[0] == SPARSE_MAGIC:
            self._parse_sparse(first)

    def __enter__(self):
        return self

    def __exit__(self, _kind, _value, _traceback):
        self.stream.close()

    def _parse_sparse(self, header: bytes) -> None:
        magic, major, _minor, file_header, chunk_header, block_size, blocks, chunks, _crc = \
            struct.unpack("<I4H4I", header)
        if magic != SPARSE_MAGIC or major != 1 or file_header < 28 or chunk_header < 12:
            raise ValueError("invalid Android sparse header")
        spans = []
        logical = 0
        self.stream.seek(file_header)
        for _ in range(chunks):
            raw = self.stream.read(chunk_header)
            if len(raw) != chunk_header:
                raise ValueError("truncated sparse chunk header")
            kind, _reserved, count, total = struct.unpack_from("<HHII", raw)
            payload = total - chunk_header
            length = count * block_size
            position = self.stream.tell()
            if kind not in (0xCAC1, 0xCAC2, 0xCAC3, 0xCAC4):
                raise ValueError("unknown sparse chunk type")
            if kind == 0xCAC1 and payload != length:
                raise ValueError("invalid raw sparse chunk")
            if kind == 0xCAC2 and payload != 4:
                raise ValueError("invalid fill sparse chunk")
            if length:
                self.starts.append(logical)
                spans.append((logical, length, kind, position))
                logical += length
            self.stream.seek(payload, 1)
        if logical != blocks * block_size:
            raise ValueError("sparse logical size mismatch")
        self.spans = spans

    def read(self, offset: int, size: int) -> bytes:
        if self.spans is None:
            self.stream.seek(offset)
            data = self.stream.read(size)
            if len(data) != size:
                raise ValueError("read beyond raw super image")
            return data
        output = bytearray()
        while size:
            index = bisect.bisect_right(self.starts, offset) - 1
            if index < 0:
                raise ValueError("invalid sparse logical offset")
            start, length, kind, position = self.spans[index]
            within = offset - start
            count = min(size, length - within)
            if count <= 0:
                raise ValueError("sparse span gap")
            if kind == 0xCAC1:
                self.stream.seek(position + within)
                part = self.stream.read(count)
            elif kind == 0xCAC2:
                self.stream.seek(position)
                fill = self.stream.read(4)
                part = (fill * ((within % 4 + count + 3) // 4))[within % 4:within % 4 + count]
            else:
                part = bytes(count)
            if len(part) != count:
                raise ValueError("truncated sparse payload")
            output.extend(part)
            offset += count
            size -= count
        return bytes(output)


def parse_metadata(reader: ImageReader) -> list[dict]:
    geometry = reader.read(4096, 52)
    magic, size = struct.unpack_from("<II", geometry)
    if magic != GEOMETRY_MAGIC or size != 52:
        raise ValueError("invalid logical-partition geometry")
    if hashlib.sha256(geometry[:8] + bytes(32) + geometry[40:]).digest() != geometry[8:40]:
        raise ValueError("logical-partition geometry checksum mismatch")
    header = reader.read(12288, 128)
    if struct.unpack_from("<I", header)[0] != METADATA_MAGIC:
        raise ValueError("invalid logical-partition metadata")
    header_size = struct.unpack_from("<I", header, 8)[0]
    header = reader.read(12288, header_size)
    if hashlib.sha256(header[:12] + bytes(32) + header[44:]).digest() != header[12:44]:
        raise ValueError("logical-partition header checksum mismatch")
    tables_size = struct.unpack_from("<I", header, 44)[0]
    tables = reader.read(12288 + header_size, tables_size)
    if hashlib.sha256(tables).digest() != header[48:80]:
        raise ValueError("logical-partition table checksum mismatch")
    part_offset, part_count, part_size = struct.unpack_from("<III", header, 80)
    extent_offset, extent_count, extent_size = struct.unpack_from("<III", header, 92)
    if part_size != 52 or extent_size != 24:
        raise ValueError("unsupported logical-partition table layout")
    result = []
    for index in range(part_count):
        name_raw, attributes, first, count, group = struct.unpack_from(
            "<36sIIII", tables, part_offset + index * part_size)
        name = name_raw.rstrip(b"\0").decode("ascii")
        if first + count > extent_count:
            raise ValueError("logical-partition extent range overflow")
        extents = []
        for number in range(first, first + count):
            sectors, kind, physical, source = struct.unpack_from(
                "<QIQI", tables, extent_offset + number * extent_size)
            if kind != 0 or source != 0 or sectors == 0:
                raise ValueError(f"unsupported extent for {name}")
            extents.append({"sectors": sectors, "physical_sector": physical})
        result.append({"name": name, "attributes": attributes, "group": group,
                       "bytes": sum(item["sectors"] for item in extents) * SECTOR,
                       "extents": extents})
    return result


def extract(reader: ImageReader, partition: dict, output: Path) -> str:
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    digest = hashlib.sha256()
    with output.open("xb") as stream:
        for extent in partition["extents"]:
            offset = extent["physical_sector"] * SECTOR
            remaining = extent["sectors"] * SECTOR
            while remaining:
                data = reader.read(offset, min(4 * 1024 * 1024, remaining))
                stream.write(data)
                digest.update(data)
                offset += len(data)
                remaining -= len(data)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--partition")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", help="major:minor source for a read-only dm table")
    args = parser.parse_args()
    source = args.source.expanduser()
    if source.is_symlink():
        parser.error("source must not be a symlink")
    source = source.resolve(strict=True)
    mode = source.stat().st_mode
    if not (stat.S_ISREG(mode) or stat.S_ISBLK(mode)):
        parser.error("source must be a regular image or block device")
    with ImageReader(source) as reader:
        partitions = parse_metadata(reader)
        if args.partition:
            matches = [item for item in partitions if item["name"] in
                       (args.partition, args.partition + "_a")]
            if len(matches) != 1:
                parser.error(f"expected exactly one {args.partition} partition")
            selected = matches[0]
            if args.device:
                logical = 0
                selected["dm_table"] = []
                for item in selected["extents"]:
                    selected["dm_table"].append(
                        f"{logical} {item['sectors']} linear {args.device} {item['physical_sector']}")
                    logical += item["sectors"]
            if args.output:
                selected["sha256"] = extract(reader, selected, args.output)
                selected["output"] = str(args.output)
            partitions = [selected]
        elif args.output or args.device:
            parser.error("--output/--device require --partition")
    print(json.dumps(partitions, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
