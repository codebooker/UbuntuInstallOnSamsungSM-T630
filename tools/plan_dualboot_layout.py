#!/usr/bin/env python3
"""Calculate, but never apply, the reviewed SM-T630 dual-boot split."""

from __future__ import annotations

import argparse
import json


SECTOR_BYTES = 512
ALIGN_SECTORS = 2048
GIB = 1024**3

# Exact read-only observations from the DZE3 development tablet.  A future
# writer must revalidate them on-device; this planner never opens a device.
DEFAULT_DISK_SECTORS = 248_799_232
DEFAULT_CURRENT_START = 21_880_832
DEFAULT_CURRENT_SECTORS = 226_918_360
DEFAULT_MINIMUM_EXT4_BLOCKS = 9_836_055
DEFAULT_EXT4_BLOCK_BYTES = 4096


def plan_layout(
    *,
    disk_sectors: int,
    current_start: int,
    current_sectors: int,
    ubuntu_gib: int,
    minimum_ext4_blocks: int,
    ext4_block_bytes: int,
) -> dict[str, int | float | str]:
    values = (
        disk_sectors,
        current_start,
        current_sectors,
        ubuntu_gib,
        minimum_ext4_blocks,
        ext4_block_bytes,
    )
    if any(value <= 0 for value in values):
        raise ValueError("all geometry values must be positive")
    if current_start % ALIGN_SECTORS:
        raise ValueError("current userdata start is not 1 MiB aligned")

    current_end = current_start + current_sectors - 1
    if current_end >= disk_sectors:
        raise ValueError("current partition extends beyond the disk")

    ubuntu_bytes = ubuntu_gib * GIB
    if ubuntu_bytes % SECTOR_BYTES or ubuntu_bytes % ext4_block_bytes:
        raise ValueError("Ubuntu target is not sector/filesystem-block aligned")
    linux_sectors = ubuntu_bytes // SECTOR_BYTES
    linux_end = current_start + linux_sectors - 1
    android_start = linux_end + 1
    if android_start % ALIGN_SECTORS:
        raise ValueError("proposed Android start is not 1 MiB aligned")
    if android_start > current_end:
        raise ValueError("Ubuntu target leaves no Android partition")

    target_ext4_blocks = ubuntu_bytes // ext4_block_bytes
    if target_ext4_blocks <= minimum_ext4_blocks:
        raise ValueError("Ubuntu target is not above the ext4 minimum")
    android_sectors = current_end - android_start + 1
    if android_sectors * SECTOR_BYTES < 16 * GIB:
        raise ValueError("proposed Android partition is smaller than 16 GiB")

    return {
        "status": "PLAN_ONLY_NO_DEVICE_WRITES",
        "sector_bytes": SECTOR_BYTES,
        "alignment_sectors": ALIGN_SECTORS,
        "disk_sectors": disk_sectors,
        "current_partition_start": current_start,
        "current_partition_end": current_end,
        "linuxroot_partition_number": 34,
        "linuxroot_start": current_start,
        "linuxroot_end": linux_end,
        "linuxroot_sectors": linux_sectors,
        "linuxroot_gib": linux_sectors * SECTOR_BYTES / GIB,
        "userdata_partition_number": 35,
        "userdata_start": android_start,
        "userdata_end": current_end,
        "userdata_sectors": android_sectors,
        "userdata_gib": android_sectors * SECTOR_BYTES / GIB,
        "ext4_target_blocks": target_ext4_blocks,
        "ext4_minimum_blocks": minimum_ext4_blocks,
        "ext4_headroom_blocks": target_ext4_blocks - minimum_ext4_blocks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disk-sectors", type=int, default=DEFAULT_DISK_SECTORS)
    parser.add_argument("--current-start", type=int, default=DEFAULT_CURRENT_START)
    parser.add_argument("--current-sectors", type=int, default=DEFAULT_CURRENT_SECTORS)
    parser.add_argument("--ubuntu-gib", type=int, default=64)
    parser.add_argument(
        "--minimum-ext4-blocks", type=int, default=DEFAULT_MINIMUM_EXT4_BLOCKS
    )
    parser.add_argument(
        "--ext4-block-bytes", type=int, default=DEFAULT_EXT4_BLOCK_BYTES
    )
    args = parser.parse_args()
    print(
        json.dumps(
            plan_layout(
                disk_sectors=args.disk_sectors,
                current_start=args.current_start,
                current_sectors=args.current_sectors,
                ubuntu_gib=args.ubuntu_gib,
                minimum_ext4_blocks=args.minimum_ext4_blocks,
                ext4_block_bytes=args.ext4_block_bytes,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
