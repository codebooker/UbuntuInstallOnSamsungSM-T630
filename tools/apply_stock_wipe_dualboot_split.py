#!/usr/bin/env python3
"""Back up factory GPT, then authorize the exact destructive stock split."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from serial_link import Link


PHRASE = "ERASE SM-T630 FACTORY USERDATA AND CREATE DUALBOOT SPLIT"
REMOTE_TOOL = "/run/apply-stock-wipe-dualboot-split"
REMOTE_BACKUP = "/run/gpt-before-split.bin"
REMOTE_MARKER = "/run/HOST-VERIFIED-GPT-BACKUP"
REMOTE_TOKEN = "/run/AUTHORIZE-FACTORY-USERDATA-WIPE-AND-SPLIT"

BACKUP_SCRIPT = r'''set -eu
test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test "$(cat /sys/class/block/sda/size)" = 248799232
test "$(cat /sys/class/block/sda/queue/logical_block_size)" = 4096
grep -qx 'PARTNAME=userdata' /sys/class/block/sda34/uevent
test "$(cat /sys/class/block/sda34/start)" = 21880832
test "$(cat /sys/class/block/sda34/size)" = 226918360
test ! -e /sys/class/block/sda35/uevent
test ! -e /run/gpt-before-split.bin
sgdisk --verify /dev/sda >/run/gpt-before-split-verify.txt 2>&1
grep -q 'No problems found' /run/gpt-before-split-verify.txt
sgdisk --backup=/run/gpt-before-split.bin /dev/sda >/dev/null
test "$(stat -c %s /run/gpt-before-split.bin)" = 6656
sha256sum /run/gpt-before-split.bin
echo FACTORY_GPT_EXPORTED_IN_RAM_NO_STORAGE_WRITE
'''


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def apply(backup: Path, authorization: str) -> None:
    if authorization != PHRASE:
        raise ValueError("authorization text mismatch")
    backup = backup.expanduser()
    if backup.exists() or backup.is_symlink():
        raise ValueError("host GPT backup path must be new")
    backup.parent.resolve(strict=True)
    source = Path(__file__).resolve().parents[1] / "maintenance" / \
        "apply-stock-wipe-dualboot-split"
    if not source.is_file() or source.is_symlink():
        raise ValueError("stock split transaction helper is absent or unsafe")

    with Link() as link:
        link.upload_file_ram(source, REMOTE_TOOL)
        result = link.run(BACKUP_SCRIPT, timeout=60)
        if "FACTORY_GPT_EXPORTED_IN_RAM_NO_STORAGE_WRITE" not in result:
            raise RuntimeError("tablet did not export the exact factory GPT")
        remote_digest = link.download_ram(REMOTE_BACKUP, backup)
        if backup.stat().st_size != 6656 or digest(backup) != remote_digest:
            raise RuntimeError("host GPT backup verification failed")
        link.upload_ram(
            f"HOST_SAVED_GPT_SHA256={remote_digest}\n".encode(), REMOTE_MARKER)
        link.upload_ram((PHRASE + "\n").encode(), REMOTE_TOKEN)
        result = link.run(f"sh {REMOTE_TOOL} --apply", timeout=300)

    print(result, end="")
    if "STOCK_USERDATA_ERASED_DUALBOOT_GPT_SPLIT_APPLIED_PARTITIONS_UNFORMATTED" \
            not in result:
        raise RuntimeError("stock-to-dualboot GPT transaction did not complete")
    print(f"Host GPT recovery backup: {backup}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True, type=Path,
                        help="new host path for the exact pre-split GPT backup")
    parser.add_argument("--authorize", required=True,
                        help=f"must equal: {PHRASE}")
    args = parser.parse_args()
    apply(args.backup, args.authorize)


if __name__ == "__main__":
    main()
