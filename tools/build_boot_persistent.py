#!/usr/bin/env python3
"""Build a reproducible persistent SM-T630 release boot candidate.

This command performs local file writes only. It never opens a device or
authorizes flashing.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil
import stat
import struct
import sys

from build_boot_test import newc, run, sha, ROOT, STOCK, TOOLS, PARTITION_SIZE


STOCK_BOOT_SHA256 = "79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
KERNEL_SHA256 = "7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6"
KERNEL_RELEASE = b"5.4.274-qgki-31225846-abT630XXSBDZE3"
ROOT_UUID = "64de8544-53ea-4fdc-8946-d6b07e238630"

RAMDISK_FILES = {
    "init": ROOT / "persistent/init",
    "bin/usb-shell": ROOT / "persistent/usb-shell",
    "bin/start-ubuntu": ROOT / "persistent/start-ubuntu",
    "bin/signal-wifi-filesystem-ready": ROOT / "tools/signal_wifi_filesystem_ready.sh",
    # Safe cleanup cannot depend on Wi-Fi having updated the outer helper.
    "bin/stop-ubuntu": ROOT / "ubuntu/stop-ubuntu-remote",
    "etc/mdev.conf": ROOT / "ubuntu/mdev.conf",
}


def arm64_image(data: bytes) -> None:
    if len(data) < 1024 * 1024:
        raise ValueError("kernel Image is implausibly small")
    if struct.unpack_from("<I", data, 0x38)[0] != 0x644D5241:
        raise ValueError("kernel is not an uncompressed arm64 Image")
    if KERNEL_RELEASE not in data:
        raise ValueError("kernel release does not match the SM-T630 baseline")


def ramdisk() -> tuple[bytes, dict[str, str]]:
    busybox_path = STOCK / "busybox-package/usr/bin/busybox"
    if not busybox_path.is_file() or busybox_path.is_symlink():
        raise ValueError("verified ARM64 BusyBox payload is missing")
    busybox = busybox_path.read_bytes()
    if sha(busybox) != BUSYBOX_SHA256:
        raise ValueError("BusyBox payload checksum mismatch")
    if busybox[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", busybox, 18)[0] != 183:
        raise ValueError("BusyBox is not an ARM64 ELF64 binary")
    phoff = struct.unpack_from("<Q", busybox, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", busybox, 54)
    if any(struct.unpack_from("<I", busybox, phoff + index * phsize)[0] == 3
           for index in range(phcount)):
        raise ValueError("BusyBox must be statically linked")

    directories = ["bin", "sbin", "dev", "proc", "sys", "config", "run",
                   "root", "tmp", "etc"]
    entries = [
        (name, stat.S_IFDIR | (0o1777 if name == "tmp" else 0o755), b"", 0, 0)
        for name in directories
    ]
    entries.extend([
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3),
        ("bin/busybox", stat.S_IFREG | 0o755, busybox, 0, 0),
    ])
    source_hashes = {}
    for destination, source in RAMDISK_FILES.items():
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"missing or unsafe ramdisk source: {source}")
        data = source.read_bytes()
        data.decode("utf-8")
        mode = 0o644 if destination.startswith("etc/") else 0o755
        entries.append((destination, stat.S_IFREG | mode, data, 0, 0))
        source_hashes[destination] = sha(data)
    entries.extend([
        ("etc/passwd", stat.S_IFREG | 0o644,
         b"root:x:0:0:root:/root:/bin/sh\n", 0, 0),
        ("etc/group", stat.S_IFREG | 0o644, b"root:x:0:\n", 0, 0),
    ])
    return newc(entries), source_hashes


def build(kernel: Path, output: Path) -> dict:
    kernel = kernel.resolve(strict=True)
    if not kernel.is_file() or kernel.is_symlink():
        raise ValueError("kernel must be a regular file")
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite existing output: {output}")

    stock = STOCK / "boot.img"
    if not stock.is_file() or stock.is_symlink() or sha(stock.read_bytes()) != STOCK_BOOT_SHA256:
        raise ValueError("stock boot image checksum mismatch")
    kernel_bytes = kernel.read_bytes()
    arm64_image(kernel_bytes)
    if sha(kernel_bytes) != KERNEL_SHA256:
        raise ValueError("kernel checksum is not the accepted module-compatible build")

    cpio, source_hashes = ramdisk()
    compressed = gzip.compress(cpio, compresslevel=9, mtime=0)
    output.mkdir(parents=True)
    (output / "initramfs.cpio").write_bytes(cpio)
    ramdisk_path = output / "initramfs.cpio.gz"
    ramdisk_path.write_bytes(compressed)

    sys.path.insert(0, str(TOOLS / "aosp-mkbootimg"))
    from unpack_bootimg import unpack_bootimg

    stock_unpack = output / "stock-unpacked"
    info = unpack_bootimg(str(stock), str(stock_unpack))
    if info.header_version != 3:
        raise ValueError(f"unexpected boot header version {info.header_version}")
    args = info.format_mkbootimg_argument()
    args[args.index("--kernel") + 1] = str(kernel)
    args[args.index("--ramdisk") + 1] = str(ramdisk_path)
    image = output / "boot.img"
    run(sys.executable, TOOLS / "aosp-mkbootimg/mkbootimg.py", *args, "--output", image)
    with image.open("ab") as stream:
        stream.write(b"SEANDROIDENFORCE")
    payload_hash = sha(image.read_bytes())
    if image.stat().st_size >= PARTITION_SIZE - 65536:
        raise ValueError("boot payload does not fit the boot partition")

    avbtool = TOOLS / "aosp-avb/avbtool.py"
    run(sys.executable, avbtool, "add_hash_footer", "--image", image,
        "--partition_name", "boot", "--partition_size", PARTITION_SIZE,
        "--algorithm", "NONE", "--salt", payload_hash)
    verified = output / "verified-unpacked"
    parsed = unpack_bootimg(str(image), str(verified))
    if parsed.header_version != info.header_version:
        raise ValueError("boot header changed during repack")
    if (parsed.cmdline != info.cmdline or parsed.os_version != info.os_version or
            parsed.os_patch_level != info.os_patch_level):
        raise ValueError("stock boot metadata changed during repack")
    if (verified / "kernel").read_bytes() != kernel_bytes:
        raise ValueError("kernel changed during repack")
    if (verified / "ramdisk").read_bytes() != compressed:
        raise ValueError("ramdisk changed during repack")
    if image.stat().st_size != PARTITION_SIZE:
        raise ValueError("AVB-padded image has the wrong partition size")
    verification = run(sys.executable, avbtool, "verify_image", "--image", image)

    # These are verification scratch files, not release artifacts. Keeping
    # duplicate 49 MiB kernels and ramdisks needlessly pressures the host disk.
    (output / "initramfs.cpio").unlink()
    ramdisk_path.unlink()
    shutil.rmtree(stock_unpack)
    shutil.rmtree(verified)

    manifest = {
        "status": "OFFLINE_VALIDATED_ONLY_NOT_FLASH_APPROVED",
        "model": "SM-T630",
        "stock_build": "T630XXSBDZE3",
        "kernel_release": KERNEL_RELEASE.decode(),
        "kernel_sha256": sha(kernel_bytes),
        "boot_sha256": sha(image.read_bytes()),
        "boot_bytes": image.stat().st_size,
        "ramdisk_sha256": sha(compressed),
        "root_uuid": ROOT_UUID,
        "ramdisk_sources": source_hashes,
        "avb_verification": verification.strip(),
        "device_writes": "none; this builder only creates local artifacts",
        "retained_files": ["boot.img", "manifest.json"],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernel", type=Path,
        default=ROOT / "output/wifi-safe-checksum-v10/Image")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output/release-boot-v1")
    args = parser.parse_args()
    print(json.dumps(build(args.kernel, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
