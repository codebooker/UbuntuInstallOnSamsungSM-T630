#!/usr/bin/env python3
"""Build the read-only SM-T630 dual-boot maintenance boot image."""

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
KERNEL_SHA256 = "49b648801a751be9761bd8b2b24e9833964acbb06741d87f7db384dd2d36845d"
KERNEL_RELEASE = b"5.4.274-qgki-31225846-abT630XXSBDZE3"
UBUNTU_BOOT_SHA256 = "1403afb30d584418ea6bfc011317f33bf8073294eae355d0c05d8d61c7355e76"

MAINTENANCE_HASHES = {
    "usr/sbin/e2fsck": "e08e5d3c172369356a92c5f20f28260bba5b7ae35726144e5bdf83383dee026a",
    "usr/sbin/resize2fs": "e742981c302ad5efec590381e22910180447052f0b5eb6b999c16a4ca6da68d9",
    "usr/sbin/sgdisk": "63e47be566b364e0e85469a3822fd3115114eeb116554c9401c4a0f27a5e4f40",
    "lib/ld-linux-aarch64.so.1": "390027e5f45f236bd1838bc54bf464c5ff01d260ab9f8b415ea8276641bce505",
    "lib/aarch64-linux-gnu/libblkid.so.1": "4b0c0835eecf17b9b900f02f7ed76352b7746de7c63ca3e027cbb9df44868dfb",
    "lib/aarch64-linux-gnu/libc.so.6": "0f1905dc27dbc6715875c70527bc8da846a10084c9c483e9d8ff76dce8d69d0e",
    "lib/aarch64-linux-gnu/libcom_err.so.2": "6a9d07af8817ed06466027a77fc7f2e8972a4a0e68895738d9acdc35470f416e",
    "lib/aarch64-linux-gnu/libe2p.so.2": "1a56588e9bc241fd2fb2a0aca90286d83d648a103af927549ae9c51ef976d51d",
    "lib/aarch64-linux-gnu/libext2fs.so.2": "dc59a13fbff5218a8aad104415189fe00eda3badf984f66ec7f77487e90a8bd1",
    "lib/aarch64-linux-gnu/libgcc_s.so.1": "f2d3ad2bf0b61f6bc944cc37d7b6ab7f88d2582b41ff989ca164803f56cc5f20",
    "lib/aarch64-linux-gnu/libm.so.6": "5e0391562de36de323fb9cb0f2c1b6bd6d034c840b1dac018499f5fe4ded1b4a",
    "lib/aarch64-linux-gnu/libpopt.so.0": "3161e2e8b4fae8d4752757260ffc106a1124dee4c8548e967bec0dd0acb7996c",
    "lib/aarch64-linux-gnu/libstdc++.so.6": "6e3112d35cfc86db7ee85b27e1746f67408e2837ff8628b46386c3eabd5682a4",
    "lib/aarch64-linux-gnu/libuuid.so.1": "c5e4db4464688e9fa7a67c7219a478927de65450bcb2815fec10cb3e1b5bfc0d",
}


def arm64_elf(data: bytes, name: str) -> None:
    if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError(f"{name} is not an ARM64 ELF64 file")


def build_ramdisk() -> tuple[bytes, dict[str, str]]:
    directories = [
        "bin", "sbin", "usr", "usr/sbin", "lib", "lib/aarch64-linux-gnu", "opt",
        "dev", "proc", "sys", "config", "run", "root", "tmp", "etc",
    ]
    entries = [
        (name, stat.S_IFDIR | (0o1777 if name == "tmp" else 0o755), b"", 0, 0)
        for name in directories
    ]
    entries.extend([
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3),
    ])

    hashes: dict[str, str] = {}
    busybox = STOCK / "busybox-package/usr/bin/busybox"
    busybox_data = busybox.read_bytes()
    if sha(busybox_data) != BUSYBOX_SHA256:
        raise ValueError("verified ARM64 BusyBox payload mismatch")
    arm64_elf(busybox_data, "busybox")
    entries.append(("bin/busybox", stat.S_IFREG | 0o755, busybox_data, 0, 0))
    hashes["bin/busybox"] = sha(busybox_data)

    scripts = {
        "init": ROOT / "maintenance/init",
        "bin/usb-shell": ROOT / "maintenance/usb-shell",
        "bin/dualboot-preflight": ROOT / "maintenance/dualboot-preflight",
        "bin/restore-ubuntu-boot": ROOT / "maintenance/restore-ubuntu-boot",
        "etc/mdev.conf": ROOT / "ubuntu/mdev.conf",
    }
    for destination, source in scripts.items():
        data = source.read_bytes()
        data.decode("utf-8")
        mode = 0o644 if destination.startswith("etc/") else 0o755
        entries.append((destination, stat.S_IFREG | mode, data, 0, 0))
        hashes[destination] = sha(data)

    source_root = STOCK / "maintenance-tools"
    for destination, expected in sorted(MAINTENANCE_HASHES.items()):
        source = source_root / destination
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"missing maintenance input: {destination}")
        data = source.read_bytes()
        if sha(data) != expected:
            raise ValueError(f"maintenance input hash mismatch: {destination}")
        arm64_elf(data, destination)
        mode = 0o755 if destination.startswith("usr/sbin/") or destination.startswith("lib/ld-") else 0o644
        entries.append((destination, stat.S_IFREG | mode, data, 0, 0))
        hashes[destination] = expected

    entries.extend([
        ("etc/passwd", stat.S_IFREG | 0o644, b"root:x:0:0:root:/root:/bin/sh\n", 0, 0),
        ("etc/group", stat.S_IFREG | 0o644, b"root:x:0:\n", 0, 0),
    ])

    ubuntu_boot = ROOT / "output/waydroid-kernel-v13/boot.img"
    ubuntu_boot_data = ubuntu_boot.read_bytes()
    if sha(ubuntu_boot_data) != UBUNTU_BOOT_SHA256 or len(ubuntu_boot_data) != PARTITION_SIZE:
        raise ValueError("accepted Ubuntu recovery BOOT mismatch")
    compressed_boot = gzip.compress(ubuntu_boot_data, compresslevel=9, mtime=0)
    entries.append((
        "opt/t630-ubuntu-boot.img.gz", stat.S_IFREG | 0o400, compressed_boot, 0, 0
    ))
    hashes["opt/t630-ubuntu-boot.img.gz"] = sha(compressed_boot)
    return newc(entries), hashes


def build(kernel: Path, output: Path) -> dict:
    kernel = kernel.resolve(strict=True)
    kernel_data = kernel.read_bytes()
    if sha(kernel_data) != KERNEL_SHA256 or KERNEL_RELEASE not in kernel_data:
        raise ValueError("kernel is not the pinned SM-T630 v13 build")
    if struct.unpack_from("<I", kernel_data, 0x38)[0] != 0x644D5241:
        raise ValueError("kernel is not an uncompressed ARM64 Image")

    stock_boot = STOCK / "boot.img"
    if sha(stock_boot.read_bytes()) != STOCK_BOOT_SHA256:
        raise ValueError("stock boot image checksum mismatch")
    output = output.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)

    cpio, source_hashes = build_ramdisk()
    compressed = gzip.compress(cpio, compresslevel=9, mtime=0)
    ramdisk = output / "maintenance.cpio.gz"
    ramdisk.write_bytes(compressed)

    sys.path.insert(0, str(TOOLS / "aosp-mkbootimg"))
    from unpack_bootimg import unpack_bootimg

    unpacked = output / "stock-unpacked"
    info = unpack_bootimg(str(stock_boot), str(unpacked))
    if info.header_version != 3:
        raise ValueError("unexpected stock boot header version")
    args = info.format_mkbootimg_argument()
    args[args.index("--kernel") + 1] = str(kernel)
    args[args.index("--ramdisk") + 1] = str(ramdisk)
    image = output / "boot.img"
    run(sys.executable, TOOLS / "aosp-mkbootimg/mkbootimg.py", *args, "--output", image)
    with image.open("ab") as stream:
        stream.write(b"SEANDROIDENFORCE")
    payload_hash = sha(image.read_bytes())
    if image.stat().st_size >= PARTITION_SIZE - 65536:
        raise ValueError("maintenance boot payload does not fit")
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
        raise ValueError("maintenance ramdisk changed during packing")
    if image.stat().st_size != PARTITION_SIZE:
        raise ValueError("AVB-padded image size mismatch")
    verification = run(sys.executable, avbtool, "verify_image", "--image", image)

    manifest = {
        "status": "OFFLINE_VALIDATED_PREFLIGHT_WITH_PINNED_BOOT_RESTORE_NOT_FLASH_APPROVED",
        "model": "SM-T630",
        "stock_build": "T630XXSBDZE3",
        "kernel_sha256": sha(kernel_data),
        "boot_sha256": sha(image.read_bytes()),
        "boot_bytes": image.stat().st_size,
        "ramdisk_sha256": sha(compressed),
        "embedded_ubuntu_boot_sha256": UBUNTU_BOOT_SHA256,
        "ramdisk_sources": source_hashes,
        "avb_verification": verification.strip(),
        "storage_behavior": "init mounts no block device; preflight is read-only; separate helper can restore only the pinned Ubuntu BOOT after explicit RAM authorization",
        "device_writes": "none; this builder only creates local artifacts",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    ramdisk.unlink()
    shutil.rmtree(unpacked)
    shutil.rmtree(verified)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", type=Path, default=ROOT / "output/waydroid-kernel-v13/Image")
    parser.add_argument("--output", type=Path, default=ROOT / "output/dualboot-maintenance-v3")
    args = parser.parse_args()
    print(json.dumps(build(args.kernel, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
