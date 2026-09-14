#!/usr/bin/python3
"""Reject identity, credentials, and completed setup state in a release root.

This is a reporting gate only. It never edits the candidate filesystem and
never prints file contents, hashes, network names, account names, or keys.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


EXACT_FORBIDDEN = (
    "etc/t630/owner",
    "etc/t630/first-boot-profile.json",
    "var/lib/dbus/machine-id",
    "var/lib/systemd/random-seed",
    "root/.bash_history",
    "root/.python_history",
)
SECRET_DIRECTORIES = (
    "etc/NetworkManager/system-connections",
    "var/lib/NetworkManager",
    "root/.ssh",
)


def nonempty_or_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if path.is_symlink():
        return True
    return not path.is_file() or info.st_size > 0


def files_below(path: Path):
    if not path.exists() or path.is_symlink():
        return []
    found = []
    for base, directories, files in os.walk(path, followlinks=False):
        directories[:] = [name for name in directories if not (Path(base) / name).is_symlink()]
        found.extend(Path(base) / name for name in files)
    return found


def human_accounts(passwd_path: Path) -> int:
    try:
        lines = passwd_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return 0
    count = 0
    for line in lines:
        fields = line.split(":")
        if len(fields) != 7:
            raise ValueError("malformed passwd database")
        uid = int(fields[2])
        if 1000 <= uid < 60000:
            count += 1
    return count


def audit(root: Path) -> list[str]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("candidate root must be a directory")
    failures = []

    for relative in EXACT_FORBIDDEN:
        if nonempty_or_link(root / relative):
            failures.append(f"identity state present: {relative}")

    machine_id = root / "etc/machine-id"
    if nonempty_or_link(machine_id):
        failures.append("machine identity is already initialized")

    for relative in SECRET_DIRECTORIES:
        path = root / relative
        if path.is_symlink() or files_below(path):
            failures.append(f"credential directory is not empty: {relative}")

    ssh = root / "etc/ssh"
    if ssh.is_dir() and any(ssh.glob("ssh_host_*key*")):
        failures.append("SSH host identity is already initialized")

    homes = root / "home"
    if homes.is_symlink() or (homes.is_dir() and any(homes.iterdir())):
        failures.append("home directory contains development or personal state")

    count = human_accounts(root / "etc/passwd")
    if count:
        failures.append(f"password database contains {count} human account(s)")

    netplan = root / "etc/netplan"
    if netplan.is_symlink() or files_below(netplan):
        failures.append("Netplan state is present; release networking must start unconfigured")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        failures = audit(args.root)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"release-root audit unavailable: {exc}\n")
    print(json.dumps({"release_safe": not failures, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
