#!/usr/bin/env python3
"""Validate the owner's exact DZE3 Samsung recovery archive without extracting it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Dict, Tuple, Union
import zipfile


MODEL = "SM-T630"
BUILD = "T630XXSBDZE3"
CSC = "XAR"
ROLES = ("BL", "AP", "HOME_CSC", "CSC")
ROLE_PATTERNS = {
    "BL": re.compile(r"^BL_T630XXSBDZE3_T630XXSBDZE3_.+\.tar\.md5$"),
    "AP": re.compile(r"^AP_T630XXSBDZE3_T630XXSBDZE3_.+\.tar\.md5$"),
    "HOME_CSC": re.compile(r"^HOME_CSC_XAR_T630XARBDZE3_.+\.tar\.md5$"),
    "CSC": re.compile(r"^CSC_XAR_T630XARBDZE3_.+\.tar\.md5$"),
}
TRAILER = re.compile(rb"([0-9a-fA-F]{32})  ([^\r\n]+\.tar)\r?\n$")


def regular_archive(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError("factory firmware must be a regular ZIP file")
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError("factory firmware must be a regular ZIP file")
    return path.resolve(strict=True)


def classify(info: zipfile.ZipInfo) -> str:
    name = info.filename
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or len(pure.parts) != 1:
        raise ValueError(f"unsafe or nested ZIP member: {name}")
    matches = [role for role, pattern in ROLE_PATTERNS.items()
               if pattern.fullmatch(name)]
    if len(matches) != 1:
        raise ValueError(f"unexpected factory ZIP member: {name}")
    if info.is_dir() or info.file_size <= 1024 * 1024:
        raise ValueError(f"implausible factory member: {name}")
    return matches[0]


def inspect(path: Path) -> Tuple[Path, zipfile.ZipFile, Dict[str, zipfile.ZipInfo]]:
    path = regular_archive(path)
    archive = zipfile.ZipFile(path)
    # Do not call testzip in the normal structural pass. The opt-in deep pass
    # below streams every byte and therefore verifies each ZIP CRC as well.
    members: Dict[str, zipfile.ZipInfo] = {}
    try:
        for info in archive.infolist():
            role = classify(info)
            if role in members:
                raise ValueError(f"duplicate factory role: {role}")
            members[role] = info
        missing = set(ROLES) - set(members)
        if missing:
            raise ValueError("missing factory roles: " + ", ".join(sorted(missing)))
    except Exception:
        archive.close()
        raise
    return path, archive, members


def verify_tar_md5(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> Dict[str, Union[str, int]]:
    digest = hashlib.md5(usedforsecurity=False)
    tail = b""
    with archive.open(info) as stream:
        while chunk := stream.read(1024 * 1024):
            combined = tail + chunk
            if len(combined) > 1024:
                digest.update(combined[:-1024])
                tail = combined[-1024:]
            else:
                tail = combined
    match = TRAILER.search(tail)
    if match is None:
        raise ValueError(f"missing Samsung MD5 trailer: {info.filename}")
    digest.update(tail[:match.start()])
    expected_name = info.filename.removesuffix(".md5")
    trailer_name = match.group(2).decode("ascii")
    if trailer_name != expected_name:
        raise ValueError(f"Samsung trailer filename mismatch: {info.filename}")
    wanted = match.group(1).decode("ascii").lower()
    actual = digest.hexdigest()
    if actual != wanted:
        raise ValueError(f"Samsung payload MD5 mismatch: {info.filename}")
    return {"payload_md5": actual, "trailer_name": trailer_name}


def validate(path: Path, deep: bool = False) -> dict:
    path, archive, members = inspect(path)
    try:
        records = []
        for role in ROLES:
            info = members[role]
            record: Dict[str, Union[str, int, bool]] = {
                "role": role,
                "name": info.filename,
                "bytes": info.file_size,
                "compressed_bytes": info.compress_size,
                "zip_crc32": f"{info.CRC:08x}",
                "deep_verified": False,
            }
            if deep:
                record.update(verify_tar_md5(archive, info))
                record["deep_verified"] = True
            records.append(record)
    finally:
        archive.close()
    return {
        "status": "RECOVERY_ARCHIVE_DEEP_VERIFIED" if deep else
                  "RECOVERY_ARCHIVE_STRUCTURE_VALID_ONLY",
        "model": MODEL,
        "build": BUILD,
        "csc": CSC,
        "archive": path.name,
        "archive_bytes": path.stat().st_size,
        "members": records,
        "warning": ("Deep verification checks ZIP CRCs and Samsung's appended MD5; "
                    "neither is a firmware authenticity signature." if deep else
                    "Run again with --deep before relying on this file for recovery."),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--deep", action="store_true",
                        help="stream every member; verify ZIP CRC and appended MD5")
    parser.add_argument("--manifest", type=Path,
                        help="write the JSON result to a new file with mode 0600")
    args = parser.parse_args()
    result = validate(args.archive.expanduser(), args.deep)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.manifest is not None:
        target = args.manifest.expanduser()
        if target.exists() or target.is_symlink():
            parser.error("manifest destination already exists")
        descriptor = os.fdopen(
            os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
            "w", encoding="utf-8")
        try:
            descriptor.write(rendered)
            descriptor.flush()
            os.fsync(descriptor.fileno())
        finally:
            descriptor.close()
    print(rendered, end="")


if __name__ == "__main__":
    main()
