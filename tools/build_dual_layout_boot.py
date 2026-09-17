#!/usr/bin/env python3
"""Build Ubuntu BOOT that accepts the reviewed whole-disk or split root."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil
import struct
import sys

from build_boot_test import run, sha, ROOT, STOCK, TOOLS, PARTITION_SIZE
from build_boot_persistent import ramdisk


STOCK_BOOT_SHA256 = "79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796"
KERNEL_SHA256 = "7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6"
KERNEL_RELEASE = b"5.4.274-qgki-31225846-abT630XXSBDZE3"


def build(kernel: Path, output: Path) -> dict:
    kernel = kernel.resolve(strict=True)
    kernel_data = kernel.read_bytes()
    if sha(kernel_data) != KERNEL_SHA256 or KERNEL_RELEASE not in kernel_data:
        raise ValueError("kernel is not the pinned module-compatible SM-T630 v12 build")
    if struct.unpack_from("<I", kernel_data, 0x38)[0] != 0x644D5241:
        raise ValueError("kernel is not an uncompressed ARM64 Image")

    stock_boot = STOCK / "boot.img"
    if sha(stock_boot.read_bytes()) != STOCK_BOOT_SHA256:
        raise ValueError("stock boot image checksum mismatch")
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)

    cpio, source_hashes = ramdisk()
    compressed = gzip.compress(cpio, compresslevel=9, mtime=0)
    ramdisk_path = output / "initramfs.cpio.gz"
    ramdisk_path.write_bytes(compressed)

    sys.path.insert(0, str(TOOLS / "aosp-mkbootimg"))
    from unpack_bootimg import unpack_bootimg

    unpacked = output / "stock-unpacked"
    info = unpack_bootimg(str(stock_boot), str(unpacked))
    if info.header_version != 3:
        raise ValueError("unexpected stock boot header version")
    args = info.format_mkbootimg_argument()
    args[args.index("--kernel") + 1] = str(kernel)
    args[args.index("--ramdisk") + 1] = str(ramdisk_path)
    image = output / "boot.img"
    run(sys.executable, TOOLS / "aosp-mkbootimg/mkbootimg.py", *args, "--output", image)
    with image.open("ab") as stream:
        stream.write(b"SEANDROIDENFORCE")
    payload_hash = sha(image.read_bytes())
    if image.stat().st_size >= PARTITION_SIZE - 65536:
        raise ValueError("dual-layout boot payload does not fit")
    avbtool = TOOLS / "aosp-avb/avbtool.py"
    run(sys.executable, avbtool, "add_hash_footer", "--image", image,
        "--partition_name", "boot", "--partition_size", PARTITION_SIZE,
        "--algorithm", "NONE", "--salt", payload_hash)

    verified = output / "verified-unpacked"
    parsed = unpack_bootimg(str(image), str(verified))
    if parsed.header_version != 3 or parsed.cmdline != info.cmdline:
        raise ValueError("boot metadata changed")
    if (verified / "kernel").read_bytes() != kernel_data:
        raise ValueError("kernel changed during packing")
    if (verified / "ramdisk").read_bytes() != compressed:
        raise ValueError("ramdisk changed during packing")
    if image.stat().st_size != PARTITION_SIZE:
        raise ValueError("AVB-padded image size mismatch")
    verification = run(sys.executable, avbtool, "verify_image", "--image", image)

    manifest = {
        "status": "OFFLINE_VALIDATED_DUAL_LAYOUT_NOT_FLASH_APPROVED",
        "model": "SM-T630",
        "stock_build": "T630XXSBDZE3",
        "accepted_root_layouts": [
            {"partition": 34, "name": "userdata", "sysfs_sectors": 226918360},
            {"partition": 34, "name": "linuxroot", "sysfs_sectors": 134217728},
        ],
        "root_uuid": "64de8544-53ea-4fdc-8946-d6b07e238630",
        "kernel_sha256": sha(kernel_data),
        "boot_sha256": sha(image.read_bytes()),
        "boot_bytes": image.stat().st_size,
        "ramdisk_sha256": sha(compressed),
        "ramdisk_sources": source_hashes,
        "avb_verification": verification.strip(),
        "device_writes": "none; this builder only creates local artifacts",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    ramdisk_path.unlink()
    shutil.rmtree(unpacked)
    shutil.rmtree(verified)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, default=ROOT / "output/wifi-safe-checksum-v10/Image")
    parser.add_argument("--output", type=Path, default=ROOT / "output/dual-layout-ubuntu-v2")
    args = parser.parse_args()
    print(json.dumps(build(args.kernel, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
