#!/usr/bin/env python3

import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest


SOURCE = Path(__file__).with_name("extract_dynamic_partition.py")
SPEC = importlib.util.spec_from_file_location("extract_dynamic_partition", SOURCE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class DynamicPartitionTests(unittest.TestCase):
    def image(self, path: Path) -> bytes:
        data = bytearray(2 * 1024 * 1024)
        geometry = bytearray(52)
        struct.pack_into("<II", geometry, 0, module.GEOMETRY_MAGIC, 52)
        geometry[8:40] = hashlib.sha256(geometry[:8] + bytes(32) + geometry[40:]).digest()
        data[4096:4148] = geometry
        partition = struct.pack("<36sIIII", b"vendor_a", 0, 0, 1, 0)
        extent = struct.pack("<QIQI", 2, 0, 2048, 0)
        tables = partition + extent
        header = bytearray(128)
        struct.pack_into("<I", header, 0, module.METADATA_MAGIC)
        struct.pack_into("<I", header, 8, 128)
        struct.pack_into("<I", header, 44, len(tables))
        header[48:80] = hashlib.sha256(tables).digest()
        struct.pack_into("<III", header, 80, 0, 1, 52)
        struct.pack_into("<III", header, 92, 52, 1, 24)
        header[12:44] = hashlib.sha256(header[:12] + bytes(32) + header[44:]).digest()
        data[12288:12416] = header
        data[12416:12416 + len(tables)] = tables
        payload = bytes(range(256)) * 4
        data[2048 * 512:2048 * 512 + len(payload)] = payload
        path.write_bytes(data)
        return payload

    def test_raw_metadata_and_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "super.img"
            payload = self.image(source)
            with module.ImageReader(source) as reader:
                parts = module.parse_metadata(reader)
                self.assertEqual(parts[0]["name"], "vendor_a")
                self.assertEqual(parts[0]["bytes"], 1024)
                output = root / "vendor.img"
                digest = module.extract(reader, parts[0], output)
                self.assertEqual(output.read_bytes(), payload)
                self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
                with self.assertRaisesRegex(ValueError, "already exists"):
                    module.extract(reader, parts[0], output)

    def test_bad_geometry_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.img"
            path.write_bytes(bytes(16384))
            with module.ImageReader(path) as reader:
                with self.assertRaisesRegex(ValueError, "geometry"):
                    module.parse_metadata(reader)


if __name__ == "__main__":
    unittest.main()
