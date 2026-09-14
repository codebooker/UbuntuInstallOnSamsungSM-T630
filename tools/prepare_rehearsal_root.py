#!/usr/bin/env python3
"""Create an identity-clean SM-T630 release rehearsal root from Ubuntu Base."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from assemble_release_root import OFFLINE_MARKER
from audit_release_root import audit


ARCHIVE_NAME = "ubuntu-base-24.04.5-base-arm64.tar.gz"
ARCHIVE_SHA256 = "a91d5a93010193712d346d761372b7c9db6dfcf093893161c64ca107f05914f2"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def validate_destination(destination: Path) -> Path:
    if destination == Path("/") or destination.is_symlink() or destination.exists():
        raise ValueError("destination must be a new, real directory")
    parent = destination.parent.resolve(strict=True)
    if parent == Path("/"):
        raise ValueError("destination must be below a dedicated parent directory")
    return parent / destination.name


def archive_members(archive: Path) -> list[str]:
    result = subprocess.run(
        ["tar", "-tzf", archive], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    members = result.stdout.splitlines()
    if not members:
        raise ValueError("Ubuntu Base archive is empty")
    for member in members:
        path = Path(member)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Ubuntu Base archive contains an unsafe path")
    return members


def prepare(archive: Path, destination: Path) -> dict:
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("Ubuntu Base archive must be a regular file")
    archive = archive.resolve(strict=True)
    if archive.name != ARCHIVE_NAME:
        raise ValueError(f"expected archive name {ARCHIVE_NAME}")
    actual = digest(archive)
    if actual != ARCHIVE_SHA256:
        raise ValueError("Ubuntu Base archive checksum mismatch")
    members = archive_members(archive)
    destination = validate_destination(destination)
    destination.mkdir(mode=0o755)
    try:
        subprocess.run(
            ["tar", "-xzf", archive, "--numeric-owner", "-C", destination],
            check=True)
        (destination / ".t630-offline-root").write_text(
            OFFLINE_MARKER, encoding="utf-8")
        failures = audit(destination)
        if failures:
            raise ValueError("new rehearsal root failed identity audit: " +
                             "; ".join(failures))
    except Exception:
        shutil.rmtree(destination)
        raise
    return {
        "archive": archive.name,
        "archive_sha256": actual,
        "archive_members": len(members),
        "destination": str(destination),
        "identity_clean": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.destination), indent=2,
                     sort_keys=True))


if __name__ == "__main__":
    main()
