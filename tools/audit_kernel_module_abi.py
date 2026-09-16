#!/usr/bin/env python3
"""Audit an ARM64 kernel module's imported symbol CRCs without rewriting it."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
VERSION_RECORD = struct.Struct("<Q56s")


def elf_sections(data: bytes) -> dict[str, bytes]:
    if len(data) < ELF_HEADER.size:
        raise ValueError("file is too short to be an ELF file")
    header = ELF_HEADER.unpack_from(data)
    ident = header[0]
    if ident[:4] != b"\x7fELF" or ident[4] != 2 or ident[5] != 1:
        raise ValueError("expected a little-endian ELF64 file")
    section_offset = header[6]
    section_size = header[11]
    section_count = header[12]
    string_index = header[13]
    if section_size != SECTION_HEADER.size or string_index >= section_count:
        raise ValueError("unsupported ELF section table")

    headers = []
    for index in range(section_count):
        offset = section_offset + index * section_size
        if offset + section_size > len(data):
            raise ValueError("truncated ELF section table")
        headers.append(SECTION_HEADER.unpack_from(data, offset))

    strings_header = headers[string_index]
    strings = data[strings_header[4]:strings_header[4] + strings_header[5]]
    sections: dict[str, bytes] = {}
    for section in headers:
        name_offset = section[0]
        if name_offset >= len(strings):
            raise ValueError("invalid ELF section name")
        name = strings[name_offset:].split(b"\0", 1)[0].decode("ascii")
        section_type = section[1]
        start, size = section[4], section[5]
        # SHT_NOBITS (notably .bss) occupies memory but has no file payload.
        if section_type == 8:
            sections[name] = b""
            continue
        if start + size > len(data):
            raise ValueError(f"truncated ELF section: {name}")
        sections[name] = data[start:start + size]
    return sections


def parse_versions_blob(data: bytes) -> dict[str, int]:
    if len(data) % VERSION_RECORD.size:
        raise ValueError("__versions size is not a whole number of records")
    versions: dict[str, int] = {}
    for offset in range(0, len(data), VERSION_RECORD.size):
        crc, raw_name = VERSION_RECORD.unpack_from(data, offset)
        name = raw_name.split(b"\0", 1)[0].decode("ascii")
        if not name:
            raise ValueError("empty symbol in __versions")
        if crc >> 32:
            raise ValueError(f"non-32-bit CRC for {name}")
        versions[name] = crc
    return versions


def parse_modinfo_blob(data: bytes) -> dict[str, str]:
    result = {}
    for item in data.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        result[key.decode("ascii")] = value.decode("utf-8", "replace")
    return result


def parse_symvers_text(text: str) -> dict[str, int]:
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 2:
            raise ValueError(f"malformed Module.symvers line {number}")
        result[fields[1]] = int(fields[0], 16)
    return result


def audit(imports: dict[str, int], exports: dict[str, int]) -> tuple[list[str], list[str]]:
    missing = sorted(name for name in imports if name not in exports)
    mismatched = sorted(
        name for name, crc in imports.items()
        if name in exports and exports[name] != crc
    )
    return missing, mismatched


def read_module(path: Path) -> tuple[dict[str, int], dict[str, str]]:
    sections = elf_sections(path.read_bytes())
    if "__versions" not in sections:
        raise ValueError("module has no __versions section")
    return (
        parse_versions_blob(sections["__versions"]),
        parse_modinfo_blob(sections.get(".modinfo", b"")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    parser.add_argument("symvers", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--expected-vermagic-prefix")
    args = parser.parse_args()

    imports, info = read_module(args.module)
    exports = parse_symvers_text(args.symvers.read_text())
    missing, mismatched = audit(imports, exports)
    vermagic = info.get("vermagic", "")

    print(f"module={args.module}")
    print(f"vermagic={vermagic}")
    print(f"depends={info.get('depends', '')}")
    print(f"imports={len(imports)} missing={len(missing)} mismatched={len(mismatched)}")
    if missing:
        print("missing_symbols=" + ",".join(missing))
    if mismatched:
        print("mismatched_symbols=" + ",".join(mismatched))

    if args.reference:
        reference, _ = read_module(args.reference)
        common = imports.keys() & reference.keys()
        same = sum(imports[name] == reference[name] for name in common)
        print(
            f"reference_imports={len(reference)} common={len(common)} "
            f"same_crc={same} different_crc={len(common) - same}"
        )
        only = sorted(reference.keys() - imports.keys())
        if only:
            print("reference_only_symbols=" + ",".join(only))

    wrong_vermagic = bool(
        args.expected_vermagic_prefix
        and not vermagic.startswith(args.expected_vermagic_prefix + " ")
    )
    if wrong_vermagic:
        print("wrong_vermagic=1")
    return 1 if missing or mismatched or wrong_vermagic else 0


if __name__ == "__main__":
    raise SystemExit(main())
