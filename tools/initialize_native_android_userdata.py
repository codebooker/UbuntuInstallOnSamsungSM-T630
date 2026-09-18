#!/usr/bin/env python3
"""Back up state and stage the guarded stock-recovery Android data initializer."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shlex

from build_recovery_bcb import build_wipe_data_message
from serial_link import Link


ROOT = Path(__file__).resolve().parents[1]
STAGER = ROOT / "tools/stage_stock_recovery_wipe.sh"
AUTHORIZATION = "INITIALIZE SM-T630 NATIVE ANDROID USERDATA WITH STOCK RECOVERY"
REMOTE = {
    "stager": "/run/t630-stage-stock-recovery-wipe.sh",
    "bcb": "/run/t630-recovery-wipe-data-bcb.bin",
    "misc": "/run/t630-misc-before-recovery.bin",
    "metadata": "/run/t630-metadata-before-android-init.bin",
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def command_script(misc_hash: str, metadata_hash: str, mode: str) -> str:
    values = {
        "misc": misc_hash,
        "metadata": metadata_hash,
        "authorization": AUTHORIZATION,
        "mode": mode,
    }
    for value in values.values():
        if "\n" in value:
            raise ValueError("newline in fixed staging value")
    return f"""set -eu
root=/run/ubuntu
test -d "$root/tmp"
for path in \\
 "$root/tmp/t630-stage-stock-recovery-wipe.sh" \\
 "$root/tmp/t630-recovery-wipe-data-bcb.bin" \\
 "$root/tmp/t630-misc-before-recovery.bin" \\
 "$root/tmp/t630-metadata-before-android-init.bin" \\
 "$root/tmp/HOST-VERIFIED-MISC-BACKUP" \\
 "$root/tmp/HOST-VERIFIED-METADATA-BACKUP" \\
 "$root/tmp/AUTHORIZE-STOCK-RECOVERY-WIPE"; do
 test ! -e "$path"
done
cp {shlex.quote(REMOTE['stager'])} "$root/tmp/t630-stage-stock-recovery-wipe.sh"
cp {shlex.quote(REMOTE['bcb'])} "$root/tmp/t630-recovery-wipe-data-bcb.bin"
cp {shlex.quote(REMOTE['misc'])} "$root/tmp/t630-misc-before-recovery.bin"
cp {shlex.quote(REMOTE['metadata'])} "$root/tmp/t630-metadata-before-android-init.bin"
printf '%s\n' {shlex.quote('HOST_SAVED_MISC_SHA256=' + misc_hash)} > "$root/tmp/HOST-VERIFIED-MISC-BACKUP"
printf '%s\n' {shlex.quote('HOST_SAVED_METADATA_SHA256=' + metadata_hash)} > "$root/tmp/HOST-VERIFIED-METADATA-BACKUP"
printf '%s\n' {shlex.quote(AUTHORIZATION)} > "$root/tmp/AUTHORIZE-STOCK-RECOVERY-WIPE"
chown 0:0 "$root/tmp/t630-stage-stock-recovery-wipe.sh" \\
 "$root/tmp/t630-recovery-wipe-data-bcb.bin" \\
 "$root/tmp/t630-misc-before-recovery.bin" \\
 "$root/tmp/t630-metadata-before-android-init.bin" \\
 "$root/tmp/HOST-VERIFIED-MISC-BACKUP" \\
 "$root/tmp/HOST-VERIFIED-METADATA-BACKUP" \\
 "$root/tmp/AUTHORIZE-STOCK-RECOVERY-WIPE"
chmod 0700 "$root/tmp/t630-stage-stock-recovery-wipe.sh"
chmod 0600 "$root/tmp/t630-recovery-wipe-data-bcb.bin" \\
 "$root/tmp/t630-misc-before-recovery.bin" \\
 "$root/tmp/t630-metadata-before-android-init.bin" \\
 "$root/tmp/HOST-VERIFIED-MISC-BACKUP" \\
 "$root/tmp/HOST-VERIFIED-METADATA-BACKUP" \\
 "$root/tmp/AUTHORIZE-STOCK-RECOVERY-WIPE"
chroot "$root" /bin/sh /tmp/t630-stage-stock-recovery-wipe.sh --check
if test {shlex.quote(mode)} = --stage; then
 chroot "$root" /bin/sh /tmp/t630-stage-stock-recovery-wipe.sh --stage
fi
rm -f {shlex.quote(REMOTE['stager'])} {shlex.quote(REMOTE['bcb'])} \\
 {shlex.quote(REMOTE['misc'])} {shlex.quote(REMOTE['metadata'])}
"""


def initialize(backup_dir: Path, apply: bool, authorization: str | None) -> None:
    if apply and authorization != AUTHORIZATION:
        raise ValueError("exact recovery-wipe authorization is required")
    if backup_dir.exists() or backup_dir.is_symlink():
        raise ValueError("backup directory must not already exist")
    backup_dir.mkdir(mode=0o700, parents=False)
    misc = backup_dir / "misc-before-android-init.bin"
    metadata = backup_dir / "metadata-before-android-init.bin"
    bcb = backup_dir / "recovery-wipe-data-bcb.bin"
    bcb.write_bytes(build_wipe_data_message())
    os.chmod(bcb, 0o600)

    with Link() as link:
        preflight = link.run(
            "set -eu; test -b /dev/sda10; test -b /dev/sda25; "
            "test -d /run/ubuntu; test ! -e /run/t630-misc-before-recovery.bin; "
            "test ! -e /run/t630-metadata-before-android-init.bin; "
            "dd if=/dev/sda10 of=/run/t630-misc-before-recovery.bin "
            "bs=1048576 count=1 status=none; "
            "dd if=/dev/sda25 of=/run/t630-metadata-before-android-init.bin "
            "bs=1048576 count=16 status=none",
            timeout=60,
        )
        if "REMOTE_EXIT=0" not in preflight:
            raise RuntimeError("tablet backup preflight failed")
        link.download_ram(REMOTE["misc"], misc)
        link.download_ram(REMOTE["metadata"], metadata)
        os.chmod(misc, 0o600)
        os.chmod(metadata, 0o600)
        link.upload_file_ram(STAGER, REMOTE["stager"])
        link.upload_file_ram(bcb, REMOTE["bcb"])
        result = link.run(
            command_script(digest(misc), digest(metadata),
                           "--stage" if apply else "--check"),
            timeout=240,
        )
    wanted = ("STOCK_RECOVERY_WIPE_BCB_STAGED_RESTART_WITH_ORDERLY_HELPER"
              if apply else "STOCK_RECOVERY_WIPE_READY_NO_CHANGES")
    if wanted not in result or "REMOTE_EXIT=0" not in result:
        raise RuntimeError(f"recovery initialization gate failed:\n{result}")
    print(result, end="")
    print(f"HOST_BACKUPS={backup_dir}")
    if apply:
        print("RECOVERY_BCB_STAGED_USE_ORDERLY_RESTART")
    else:
        print("READ_ONLY_GATE_PASSED_RERUN_WITH_EXACT_AUTHORIZATION_TO_STAGE")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--authorization")
    args = parser.parse_args()
    initialize(args.backup_dir, args.apply, args.authorization)


if __name__ == "__main__":
    main()
