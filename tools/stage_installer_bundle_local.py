#!/usr/bin/env python3
"""Copy a sealed on-tablet bundle from linuxroot into guarded recovery RAM."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex

from serial_link import Link


STAGING = "/run/t630-installer"
FILES = (
    "t630-release-rootfs.tar.gz",
    "t630-release-rootfs.tar.gz.manifest.json",
    "t630-installer-runtime.tar.gz",
    "t630-installer-runtime.tar.gz.manifest.json",
    "boot/boot.img",
    "boot/manifest.json",
    "installer-bundle.json",
)
EXPECTED_BOOT_SHA256 = (
    "fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f"
)


def staging_script(source: str) -> str:
    if (not source.startswith("/run/ubuntu/") or ".." in source.split("/")
            or "\n" in source or "\r" in source):
        raise ValueError("source must be an absolute userdata path below /run/ubuntu")
    quoted = shlex.quote(source.rstrip("/"))
    expected = " ".join(shlex.quote(name) for name in FILES)
    return rf'''set -eu
source={quoted}
stage={STAGING}
files='{expected}'
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
grep -qx 'PARTNAME=linuxroot' /sys/class/block/sda34/uevent
test "$(cat /sys/class/block/sda34/size)" = 134217728
grep -qx 'PARTNAME=userdata' /sys/class/block/sda35/uevent
test "$(cat /sys/class/block/sda35/size)" = 92700632
test -d "$source" && test ! -L "$source"
test "$(readlink -f "$source")" = "$source"
test ! -e "$stage"
cd "$source"
test -f SHA256SUMS && test ! -L SHA256SUMS
test "$(wc -l <SHA256SUMS)" -eq 7
awk '
    length($1) != 64 || NF != 2 {{ bad=1 }}
    NR == 1 && $2 != "t630-release-rootfs.tar.gz" {{ bad=1 }}
    NR == 2 && $2 != "t630-release-rootfs.tar.gz.manifest.json" {{ bad=1 }}
    NR == 3 && $2 != "t630-installer-runtime.tar.gz" {{ bad=1 }}
    NR == 4 && $2 != "t630-installer-runtime.tar.gz.manifest.json" {{ bad=1 }}
    NR == 5 && $2 != "boot/boot.img" {{ bad=1 }}
    NR == 6 && $2 != "boot/manifest.json" {{ bad=1 }}
    NR == 7 && $2 != "installer-bundle.json" {{ bad=1 }}
    END {{ exit (NR == 7 && !bad) ? 0 : 1 }}
' SHA256SUMS
sha256sum -c SHA256SUMS
test "$(stat -c %s boot/boot.img)" = 100663296
printf '%s  %s\n' {EXPECTED_BOOT_SHA256} boot/boot.img | sha256sum -c -
bytes=0
for name in $files SHA256SUMS; do
    test -f "$name" && test ! -L "$name"
    size=$(stat -c %s "$name")
    bytes=$((bytes + size))
done
test "$bytes" -le 4294967296
required_kib=$(((bytes + 1023) / 1024 + 512 * 1024))
available=$(awk '$1 == "MemAvailable:" {{print $2}}' /proc/meminfo)
test "$available" -ge "$required_kib"
mkdir -m 0700 "$stage"
mounted=0
cleanup() {{
    if [ "$mounted" -eq 1 ]; then umount "$stage" || true; fi
    rmdir "$stage/boot" 2>/dev/null || true
    rmdir "$stage" 2>/dev/null || true
}}
trap cleanup EXIT HUP INT TERM
mount -t tmpfs -o mode=0700,nosuid,nodev,noexec,size=$((bytes + 67108864)) \
    tmpfs "$stage"
mounted=1
mkdir -m 0700 "$stage/boot"
for name in $files SHA256SUMS; do
    cp "$source/$name" "$stage/$name"
done
cd "$stage"
sha256sum -c SHA256SUMS
grep -Fq '"status": "PRIVATE_INSTALLER_BUNDLE_SEALED_NOT_DEVICE_WRITE_AUTHORIZATION"' \
    installer-bundle.json
grep -Fq '"model": "SM-T630"' installer-bundle.json
grep -Fq '"stock_build": "T630XXSBDZE3"' installer-bundle.json
trap - EXIT HUP INT TERM
echo INSTALLER_BUNDLE_COPIED_FROM_LINUXROOT_TO_RAM_NO_DEVICE_WRITE
'''


def stage(source: str) -> None:
    with Link() as link:
        result = link.run(staging_script(source), timeout=900)
        if "INSTALLER_BUNDLE_COPIED_FROM_LINUXROOT_TO_RAM_NO_DEVICE_WRITE" not in result:
            raise RuntimeError("tablet did not complete local RAM staging")
        print(result, end="")
        installer = Path(__file__).with_name("install_staged_release.sh")
        link.upload_file_ram(installer, f"{STAGING}/install-staged-release")
        prepare = Path(__file__).with_name("prepare_staged_install.sh")
        link.upload_file_ram(prepare, f"{STAGING}/prepare-staged-install")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        help="sealed bundle directory on mounted linuxroot below /run/ubuntu")
    args = parser.parse_args()
    stage(args.source)


if __name__ == "__main__":
    main()
