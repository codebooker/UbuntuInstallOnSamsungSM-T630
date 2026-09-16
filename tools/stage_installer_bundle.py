#!/usr/bin/env python3
"""Stage a sealed SM-T630 installer bundle in tablet RAM; never write storage."""

from __future__ import annotations

import argparse
from pathlib import Path

from finalize_installer_bundle import INPUTS, verify_sealed
from serial_link import Link


STAGING = "/run/t630-installer"
ALL_FILES = ("SHA256SUMS", "installer-bundle.json") + INPUTS

VERIFY_SCRIPT = r'''set -eu
stage=/run/t630-installer
cd "$stage"
test -f SHA256SUMS
test ! -L SHA256SUMS
test "$(wc -l <SHA256SUMS)" -eq 7
awk '
    length($1) != 64 || NF != 2 { bad=1 }
    NR == 1 && $2 != "t630-release-rootfs.tar.gz" { bad=1 }
    NR == 2 && $2 != "t630-release-rootfs.tar.gz.manifest.json" { bad=1 }
    NR == 3 && $2 != "t630-installer-runtime.tar.gz" { bad=1 }
    NR == 4 && $2 != "t630-installer-runtime.tar.gz.manifest.json" { bad=1 }
    NR == 5 && $2 != "boot/boot.img" { bad=1 }
    NR == 6 && $2 != "boot/manifest.json" { bad=1 }
    NR == 7 && $2 != "installer-bundle.json" { bad=1 }
    END { exit (NR == 7 && !bad) ? 0 : 1 }
' SHA256SUMS
sha256sum -c SHA256SUMS
test "$(stat -c %s boot/boot.img)" = 100663296
printf '%s  %s\n' \
  a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28 \
  boot/boot.img | sha256sum -c -
test "$(stat -c %s t630-release-rootfs.tar.gz)" -gt 104857600
test "$(stat -c %s t630-release-rootfs.tar.gz)" -le 4294967296
grep -Fq '"status": "LOCAL_PRIVATE_INSTALLER_INPUT_DO_NOT_REDISTRIBUTE"' \
  t630-release-rootfs.tar.gz.manifest.json
grep -Fq '"status": "PRIVATE_INSTALLER_RUNTIME_ARM64_NO_DEVICE_WRITE"' \
  t630-installer-runtime.tar.gz.manifest.json
grep -Fq '"status": "PRIVATE_INSTALLER_BUNDLE_SEALED_NOT_DEVICE_WRITE_AUTHORIZATION"' \
  installer-bundle.json
grep -Fq '"model": "SM-T630"' installer-bundle.json
grep -Fq '"stock_build": "T630XXSBDZE3"' installer-bundle.json
echo INSTALLER_BUNDLE_VERIFIED_IN_RAM_NO_DEVICE_WRITE
'''


def setup_script(bytes_needed: int) -> str:
    # Leave at least 512 MiB outside the bounded staging tmpfs.
    required_kib = (bytes_needed + 1023) // 1024 + 512 * 1024
    size = bytes_needed + 64 * 1024 * 1024
    return f'''set -eu
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
grep -qx 'PARTNAME=userdata' /sys/class/block/sda34/uevent
test "$(cat /sys/class/block/sda34/size)" = 226918360
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
test ! -e {STAGING}
available=$(awk '$1 == "MemAvailable:" {{print $2}}' /proc/meminfo)
test "$available" -ge {required_kib}
mkdir -m 0700 {STAGING}
mount -t tmpfs -o mode=0700,nosuid,nodev,noexec,size={size} tmpfs {STAGING}
mkdir -m 0700 {STAGING}/boot
echo INSTALLER_RAM_STAGING_READY
'''


def stage(work: Path) -> None:
    work = work.expanduser().resolve(strict=True)
    verify_sealed(work)
    bytes_needed = sum((work / name).stat().st_size for name in ALL_FILES)
    if bytes_needed > 4 * 1024 * 1024 * 1024:
        raise ValueError("sealed bundle exceeds the 4 GiB tablet RAM staging limit")
    with Link() as link:
        prepared = link.run(setup_script(bytes_needed), timeout=30)
        if "INSTALLER_RAM_STAGING_READY" not in prepared:
            raise RuntimeError("tablet refused RAM staging")
        # Small control files arrive first; the large rootfs is deliberately last.
        order = tuple(name for name in ALL_FILES
                      if name != "t630-release-rootfs.tar.gz") + (
                          "t630-release-rootfs.tar.gz",)
        for name in order:
            print(f"Staging {name}", flush=True)
            link.upload_file_ram(work / name, f"{STAGING}/{name}")
        result = link.run(VERIFY_SCRIPT, timeout=180)
        if "INSTALLER_BUNDLE_VERIFIED_IN_RAM_NO_DEVICE_WRITE" not in result:
            raise RuntimeError("tablet-side installer bundle verification failed")
        print(result, end="")
        installer = Path(__file__).with_name("install_staged_release.sh")
        remote_installer = f"{STAGING}/install-staged-release"
        link.upload_file_ram(installer, remote_installer)
        result = link.run(f"sh {remote_installer} --check", timeout=180)
        if "INSTALLER_CHECK_PASSED_USERDATA_UNMOUNTED_NO_DEVICE_WRITE" not in result:
            raise RuntimeError("tablet-side pre-install check failed")
        print(result, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_directory", type=Path,
                        help="sealed output from build_local_installer.sh")
    args = parser.parse_args()
    stage(args.work_directory)


if __name__ == "__main__":
    main()
