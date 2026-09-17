#!/usr/bin/env python3
"""Safely prepare the exact SM-T630 DZE3 factory payload for Heimdall."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
from typing import BinaryIO
import zipfile

import verify_factory_firmware


ARCHIVE_SHA256 = "24fd9cdf0a55ae3ae84b01b7b071dec845e90288a44b572767faaa20425876d5"
PIT_NAME = "GTACT4PROWIFI_EUR_OPEN.pit"
PIT_SHA256 = "3c2eda15a7e01052b8c806f1c158f846c0783335494792341b74f9133b0578af"
MIN_FREE_BYTES = 20 * 1024**3

# Only payloads supplied by Samsung are flashed. HOME_CSC is deliberately
# excluded: the wiping CSC payload is required for a predictable stock reset.
PAYLOADS = {
    "BL": {
        "abl.elf.lz4": "ABL",
        "xbl.elf.lz4": "XBL",
        "xbl_config.elf.lz4": "XBL_CONFIG",
        "tz.mbn.lz4": "TZ",
        "hypvm.mbn.lz4": "HYP",
        "devcfg.mbn.lz4": "DEVCFG",
        "tz_iccc.mbn.lz4": "TZICCC",
        "aop.mbn.lz4": "AOP",
        "km41.mbn.lz4": "KEYMASTER",
        "qupv3fw.elf.lz4": "QUPFW",
        "storsec.mbn.lz4": "STORSEC",
        "NON-HLOS.bin.lz4": "APNHLOS",
        "dspso.bin.lz4": "DSP",
        "shrm.elf.lz4": "SHRM",
        "cpucp.elf.lz4": "CPUCP",
        "uefi_sec.mbn.lz4": "UEFISECAPP",
        "imagefv.elf.lz4": "IMAGEFV",
        "sec.elf.lz4": "SECDATA",
        "quest.fv.lz4": "TOOLSFV",
        "testvector.fv.lz4": "LOGDUMP",
        "bksecapp.mbn.lz4": "BKSECAPP",
        "apdp.mbn.lz4": "APDP",
        "vaultkeeper.mbn.lz4": "VK",
        "tz_kg.mbn.lz4": "TZ_KG",
        "tz_hdm.mbn.lz4": "HDM",
    },
    "AP": {
        "boot.img.lz4": "BOOT",
        "recovery.img.lz4": "RECOVERY",
        "vendor_boot.img.lz4": "VENDOR_BOOT",
        "dtbo.img.lz4": "DTBO",
        "super.img.lz4": "SUPER",
        "vbmeta.img.lz4": "VBMETA",
        "vbmeta_system.img.lz4": "VBMETA_SYSTEM",
        "userdata.img.lz4": "USERDATA",
        "persist.img.lz4": "PERSIST",
        "misc.bin.lz4": "MISC",
        "modem.bin.lz4": "MODEM",
    },
    "CSC": {
        PIT_NAME: None,
        "cache.img.lz4": "CACHE",
        "omr.img.lz4": "OMR",
        "prism.img.lz4": "PRISM",
        "optics.img.lz4": "OPTICS",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_regular(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"{label} must be a regular file")
    return path.resolve(strict=True)


def copy_exact(source: BinaryIO, target: Path) -> None:
    with target.open("xb") as output:
        os.chmod(target, 0o600)
        shutil.copyfileobj(source, output, length=1024 * 1024)
        output.flush()
        os.fsync(output.fileno())


def decompress_lz4(source: BinaryIO, target: Path, lz4: Path) -> None:
    with target.open("xb") as output:
        os.chmod(target, 0o600)
        process = subprocess.Popen(
            [str(lz4), "-d", "-c"], stdin=subprocess.PIPE, stdout=output,
            stderr=subprocess.PIPE)
        assert process.stdin is not None
        try:
            while chunk := source.read(1024 * 1024):
                process.stdin.write(chunk)
            process.stdin.close()
            stderr = process.stderr.read() if process.stderr else b""
            result = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise
        if result != 0:
            raise ValueError(
                f"LZ4 decompression failed for {target.name}: "
                + stderr.decode(errors="replace"))
        output.flush()
        os.fsync(output.fileno())


def extract_role(
        archive: zipfile.ZipFile, info: zipfile.ZipInfo, role: str,
        output: Path, lz4: Path) -> list[dict]:
    wanted = PAYLOADS[role]
    seen: set[str] = set()
    records: list[dict] = []
    with archive.open(info) as outer:
        with tarfile.open(fileobj=outer, mode="r|") as inner:
            for member in inner:
                pure = PurePosixPath(member.name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise ValueError(f"unsafe {role} member: {member.name}")
                if member.name not in wanted:
                    continue
                if member.name in seen or not member.isreg() or member.size <= 0:
                    raise ValueError(f"invalid {role} payload: {member.name}")
                seen.add(member.name)
                source = inner.extractfile(member)
                if source is None:
                    raise ValueError(f"could not read {role} payload: {member.name}")
                target_name = member.name.removesuffix(".lz4")
                target = output / target_name
                print(f"Preparing {role}/{member.name} ...", flush=True)
                if member.name.endswith(".lz4"):
                    decompress_lz4(source, target, lz4)
                else:
                    copy_exact(source, target)
                record = {
                    "role": role,
                    "source": member.name,
                    "file": target.name,
                    "partition": wanted[member.name],
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                }
                records.append(record)
        # Drain through the ZIP member boundary so Python validates its CRC.
        while outer.read(1024 * 1024):
            pass
    missing = set(wanted) - seen
    if missing:
        raise ValueError(f"missing {role} payloads: {', '.join(sorted(missing))}")
    return records


def prepare(archive_path: Path, output: Path) -> dict:
    archive_path = require_regular(archive_path, "factory firmware")
    if sha256(archive_path) != ARCHIVE_SHA256:
        raise ValueError("factory ZIP SHA-256 does not match the accepted DZE3 archive")
    if output.exists() or output.is_symlink():
        raise ValueError("output directory must not already exist")
    free = shutil.disk_usage(output.parent.resolve()).free
    if free < MIN_FREE_BYTES:
        raise ValueError("at least 20 GiB of free space is required")
    lz4_name = shutil.which("lz4")
    if not lz4_name:
        raise ValueError("lz4 is required")
    lz4 = Path(lz4_name).resolve(strict=True)

    # This streams all four Samsung archives first, validating ZIP CRCs,
    # appended MD5s, and the exact inner allowlists before creating output.
    verified = verify_factory_firmware.validate(
        archive_path, deep=True, inventory=True)
    members = {item["role"]: item for item in verified["members"]}

    output.mkdir(mode=0o700)
    try:
        records: list[dict] = []
        with zipfile.ZipFile(archive_path) as archive:
            infos = {info.filename: info for info in archive.infolist()}
            for role in ("BL", "AP", "CSC"):
                info = infos[members[role]["name"]]
                records.extend(extract_role(archive, info, role, output, lz4))
        pit = output / PIT_NAME
        if sha256(pit) != PIT_SHA256:
            raise ValueError("factory PIT hash mismatch")
        partitions = [item["partition"] for item in records
                      if item["partition"] is not None]
        if len(partitions) != len(set(partitions)):
            raise ValueError("duplicate target partition in factory payload")
        manifest = {
            "status": "SM_T630_DZE3_FACTORY_RESTORE_PREPARED",
            "model": verify_factory_firmware.MODEL,
            "build": verify_factory_firmware.BUILD,
            "csc": verify_factory_firmware.CSC,
            "archive": str(archive_path),
            "archive_sha256": ARCHIVE_SHA256,
            "wiping_csc": True,
            "factory_pit": PIT_NAME,
            "factory_pit_sha256": PIT_SHA256,
            "payloads": records,
        }
        target = output / "restore-manifest.json"
        with target.open("x", encoding="utf-8") as stream:
            os.chmod(target, 0o600)
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        prepare(args.archive.expanduser(), args.output.expanduser())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FACTORY_RESTORE_PREPARATION_REFUSED: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
