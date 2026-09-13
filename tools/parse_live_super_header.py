#!/usr/bin/env python3
"""Parse partition extents from the first megabyte of a raw Android super device."""

import hashlib
import json
import struct
import sys

data = sys.stdin.buffer.read()
geometry = data[4096:4148]
assert struct.unpack_from("<I", geometry)[0] == 0x616C4467
assert hashlib.sha256(geometry[:8] + bytes(32) + geometry[40:]).digest() == geometry[8:40]

header_offset = 12288
header = data[header_offset:header_offset + 128]
assert struct.unpack_from("<I", header)[0] == 0x414C5030
header_size = struct.unpack_from("<I", header, 8)[0]
header = data[header_offset:header_offset + header_size]
assert hashlib.sha256(header[:12] + bytes(32) + header[44:]).digest() == header[12:44]

table_size = struct.unpack_from("<I", header, 44)[0]
tables = data[header_offset + header_size:header_offset + header_size + table_size]
assert hashlib.sha256(tables).digest() == header[48:80]
partition_offset, partition_count, partition_size = struct.unpack_from("<III", header, 80)
extent_offset, _, extent_size = struct.unpack_from("<III", header, 92)
assert partition_size == 52 and extent_size == 24

result = []
for index in range(partition_count):
    name, attributes, first, count, group = struct.unpack_from(
        "<36sIIII", tables, partition_offset + index * partition_size
    )
    name = name.rstrip(b"\0").decode()
    extents = [
        struct.unpack_from("<QIQI", tables, extent_offset + item * extent_size)
        for item in range(first, first + count)
    ]
    result.append({
        "name": name,
        "attributes": attributes,
        "bytes": sum(extent[0] * 512 for extent in extents),
        "extents": extents,
    })

json.dump(result, sys.stdout, indent=2)
