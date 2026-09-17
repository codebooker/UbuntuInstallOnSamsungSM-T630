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
import tarfile
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
EXPECTED_INNER = {
    "BL": {
        "abl.elf.lz4", "xbl.elf.lz4", "xbl_config.elf.lz4", "tz.mbn.lz4",
        "hypvm.mbn.lz4", "devcfg.mbn.lz4", "tz_iccc.mbn.lz4", "aop.mbn.lz4",
        "km41.mbn.lz4", "qupv3fw.elf.lz4", "storsec.mbn.lz4", "NON-HLOS.bin.lz4",
        "dspso.bin.lz4", "shrm.elf.lz4", "cpucp.elf.lz4", "uefi_sec.mbn.lz4",
        "imagefv.elf.lz4", "sec.elf.lz4", "quest.fv.lz4", "testvector.fv.lz4",
        "bksecapp.mbn.lz4", "apdp.mbn.lz4", "vbmeta.img.lz4",
        "vaultkeeper.mbn.lz4", "tz_kg.mbn.lz4", "tz_hdm.mbn.lz4",
    },
    "AP": {
        "boot.img.lz4", "recovery.img.lz4", "vendor_boot.img.lz4", "dtbo.img.lz4",
        "super.img.lz4", "vbmeta.img.lz4", "vbmeta_system.img.lz4",
        "userdata.img.lz4", "persist.img.lz4", "misc.bin.lz4", "modem.bin.lz4",
        "meta-data", "meta-data/fota.zip",
    },
    "HOME_CSC": {
        "cache.img.lz4", "prism.img.lz4", "optics.img.lz4", "meta-data",
        "meta-data/download-list.txt",
    },
    "CSC": {
        "GTACT4PROWIFI_EUR_OPEN.pit", "cache.img.lz4", "omr.img.lz4",
        "prism.img.lz4", "optics.img.lz4", "meta-data", "meta-data/fota.zip",
    },
}


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


def verify_tar_inventory(
        archive: zipfile.ZipFile, role: str, info: zipfile.ZipInfo
) -> list[Dict[str, Union[str, int]]]:
    records: list[Dict[str, Union[str, int]]] = []
    names = set()
    with archive.open(info) as stream:
        with tarfile.open(fileobj=stream, mode="r|") as inner:
            for member in inner:
                pure = PurePosixPath(member.name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise ValueError(
                        f"unsafe inner tar member in {role}: {member.name}")
                if member.name in names:
                    raise ValueError(
                        f"duplicate inner tar member in {role}: {member.name}")
                names.add(member.name)
                if member.isdir():
                    kind = "directory"
                    if member.size != 0:
                        raise ValueError(
                            f"nonempty inner directory in {role}: {member.name}")
                elif member.isreg():
                    kind = "file"
                    if member.size <= 0:
                        raise ValueError(
                            f"empty inner payload in {role}: {member.name}")
                else:
                    raise ValueError(
                        f"unsafe inner tar type in {role}: {member.name}")
                records.append({
                    "name": member.name,
                    "bytes": member.size,
                    "type": kind,
                })
    missing = EXPECTED_INNER[role] - names
    unexpected = names - EXPECTED_INNER[role]
    if missing:
        raise ValueError(
            f"missing inner {role} members: " + ", ".join(sorted(missing)))
    if unexpected:
        raise ValueError(
            f"unexpected inner {role} members: " + ", ".join(sorted(unexpected)))
    return records


def validate(path: Path, deep: bool = False, inventory: bool = False) -> dict:
    if inventory and not deep:
        raise ValueError("inner inventory requires deep verification")
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
            if inventory:
                record["inner_members"] = verify_tar_inventory(
                    archive, role, info)
            records.append(record)
    finally:
        archive.close()
    return {
        "status": ("RECOVERY_ARCHIVE_CONTENTS_VERIFIED" if inventory else
                   "RECOVERY_ARCHIVE_DEEP_VERIFIED" if deep else
                   "RECOVERY_ARCHIVE_STRUCTURE_VALID_ONLY"),
        "model": MODEL,
        "build": BUILD,
        "csc": CSC,
        "archive": path.name,
        "archive_bytes": path.stat().st_size,
        "members": records,
        "warning": ("Deep verification checks ZIP CRCs, Samsung's appended MD5, "
                    "and optionally the exact inner member allowlist; none is a "
                    "firmware authenticity signature." if deep else
                    "Run again with --deep before relying on this file for recovery."),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--deep", action="store_true",
                        help="stream every member; verify ZIP CRC and appended MD5")
    parser.add_argument(
        "--inventory", action="store_true",
        help="with --deep, require the exact safe inner BL/AP/CSC member sets")
    parser.add_argument("--manifest", type=Path,
                        help="write the JSON result to a new file with mode 0600")
    args = parser.parse_args()
    if args.inventory and not args.deep:
        parser.error("--inventory requires --deep")
    result = validate(args.archive.expanduser(), args.deep, args.inventory)
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
