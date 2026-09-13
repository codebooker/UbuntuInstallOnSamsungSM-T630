#!/usr/bin/env python3
"""Repack the proven persistent SM-T630 boot image with a validated kernel."""

import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

from build_boot_test import PARTITION_SIZE, ROOT, TOOLS, run, sha

SOURCE_BOOT_SHA256 = "297cf31e5914ff6a17d1e1d6499d2af2a493022c56336978b76e61e14b9c910a"
KERNEL_RELEASE = b"5.4.274-qgki-31225846-abT630XXSBDZE3"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", type=Path)
    parser.add_argument("--name", default="bluetooth-h4-v2")
    parser.add_argument(
        "--purpose",
        default="Enable the H4 and Qualcomm IBS-aware Bluetooth UART transports",
    )
    args = parser.parse_args()

    kernel = args.kernel.resolve()
    source_boot = ROOT / "output/persistent-v1/boot.img"
    output = ROOT / "output" / args.name
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")

    if sha(source_boot.read_bytes()) != SOURCE_BOOT_SHA256:
        raise ValueError("the proven persistent boot image does not match its pinned hash")

    kernel_bytes = kernel.read_bytes()
    if len(kernel_bytes) < 1024 * 1024:
        raise ValueError("kernel Image is implausibly small")
    if struct.unpack_from("<I", kernel_bytes, 0x38)[0] != 0x644D5241:
        raise ValueError("kernel is not an uncompressed arm64 Image")
    if KERNEL_RELEASE not in kernel_bytes:
        raise ValueError("kernel does not contain the exact SM-T630 release string")

    output.mkdir(parents=True)

    sys.path.insert(0, str(TOOLS / "aosp-mkbootimg"))
    from unpack_bootimg import unpack_bootimg

    source_unpack = output / "source-unpacked"
    info = unpack_bootimg(str(source_boot), str(source_unpack))
    if info.header_version != 3:
        raise ValueError(f"unexpected boot header version {info.header_version}")
    mkboot_args = info.format_mkbootimg_argument()
    mkboot_args[mkboot_args.index("--kernel") + 1] = str(kernel)

    image = output / "boot.img"
    run(sys.executable, TOOLS / "aosp-mkbootimg/mkbootimg.py", *mkboot_args, "--output", image)
    with image.open("ab") as stream:
        stream.write(b"SEANDROIDENFORCE")
    payload_hash = sha(image.read_bytes())
    if image.stat().st_size >= PARTITION_SIZE - 65536:
        raise ValueError("repacked boot payload does not fit the boot partition")

    avbtool = TOOLS / "aosp-avb/avbtool.py"
    run(
        sys.executable,
        avbtool,
        "add_hash_footer",
        "--image",
        image,
        "--partition_name",
        "boot",
        "--partition_size",
        PARTITION_SIZE,
        "--algorithm",
        "NONE",
        "--salt",
        payload_hash,
    )

    verified = output / "verified-unpacked"
    parsed = unpack_bootimg(str(image), str(verified))
    if parsed.header_version != info.header_version:
        raise ValueError("boot header changed during repack")
    if (
        parsed.cmdline != info.cmdline
        or parsed.os_version != info.os_version
        or parsed.os_patch_level != info.os_patch_level
    ):
        raise ValueError("boot metadata changed during repack")
    if (verified / "kernel").read_bytes() != kernel_bytes:
        raise ValueError("kernel changed during repack")
    if (verified / "ramdisk").read_bytes() != (source_unpack / "ramdisk").read_bytes():
        raise ValueError("proven persistent ramdisk changed during repack")
    if image.stat().st_size != PARTITION_SIZE:
        raise ValueError("AVB-padded boot image does not match the boot partition size")
    verification = run(sys.executable, avbtool, "verify_image", "--image", image)

    copied_kernel = output / "Image"
    shutil.copyfile(kernel, copied_kernel)
    manifest = {
        "status": "OFFLINE_VALIDATED; physical boot not yet tested",
        "model": "SM-T630",
        "stock_build": "T630XXSBDZE3",
        "kernel_release": "5.4.274-qgki-31225846-abT630XXSBDZE3",
        "purpose": args.purpose,
        "source_boot_sha256": sha(source_boot.read_bytes()),
        "boot_sha256": sha(image.read_bytes()),
        "boot_bytes": image.stat().st_size,
        "kernel_sha256": sha(kernel_bytes),
        "ramdisk_sha256": sha((verified / "ramdisk").read_bytes()),
        "avb_verification": verification.strip(),
        "device_writes": "none; this builder only creates local artifacts",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
