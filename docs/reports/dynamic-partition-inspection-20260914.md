# Factory dynamic-partition inspection (2026-09-14)

`tools/extract_dynamic_partition.py` now verifies Android logical-partition
geometry, header, and table checksums before reporting or extracting anything.
It accepts either Samsung's sparse `super.img` or the raw physical `super`
block device, rejects unsupported extent types, refuses an existing output,
and can emit a read-only device-mapper table.

Read-only inspection of `/dev/sda26` on the exact DZE3 tablet found:

- `vendor`: 2,214,168 sectors starting at physical sector 15,142,912,
  totaling 1,133,654,016 bytes;
- `system`: 12,036,096 sectors at 2,048 plus 16,248 sectors at 17,401,856,
  totaling 6,170,800,128 bytes.

The system table is byte-for-byte the table already used by the physically
tested camera mount helper. The discovered vendor size exactly matches the old
`stock-vendor-full.img` copy. This proves a future installer can mount both
logical partitions read-only from the untouched physical `super` partition and
avoid storing another 1.1 GB vendor image in a selected user's home directory.

The parser has synthetic raw-image tests for checksum validation, partition
selection, bounded extraction, output collision refusal, and corrupt-geometry
rejection. No block device was written during physical inspection.
