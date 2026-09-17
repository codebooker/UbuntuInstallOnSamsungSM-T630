#!/usr/bin/env python3
"""Guard and execute the exact wiping SM-T630 DZE3 Heimdall restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

import prepare_factory_restore


AUTHORIZATION = "ERASE SM-T630 LINUXROOT"
EXPECTED_STATUS = "SM_T630_DZE3_FACTORY_RESTORE_PREPARED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"{label} must be a regular file")
    return path.resolve(strict=True)


def expected_payloads() -> set[tuple[str, str, str, str | None]]:
    result = set()
    for role, members in prepare_factory_restore.PAYLOADS.items():
        for source, partition in members.items():
            result.add((role, source, source.removesuffix(".lz4"), partition))
    return result


def validate_manifest(manifest_path: Path) -> tuple[Path, list[tuple[str, Path]]]:
    manifest_path = regular(manifest_path, "restore manifest")
    root = manifest_path.parent
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (data.get("status") != EXPECTED_STATUS or
            data.get("model") != "SM-T630" or
            data.get("build") != "T630XXSBDZE3" or
            data.get("csc") != "XAR" or
            data.get("archive_sha256") != prepare_factory_restore.ARCHIVE_SHA256 or
            data.get("factory_pit_sha256") != prepare_factory_restore.PIT_SHA256 or
            data.get("wiping_csc") is not True):
        raise ValueError("restore manifest identity mismatch")
    payloads = data.get("payloads")
    if not isinstance(payloads, list):
        raise ValueError("restore manifest payload list is absent")
    actual = set()
    flash: list[tuple[str, Path]] = []
    for item in payloads:
        try:
            role = item["role"]
            source = item["source"]
            filename = item["file"]
            partition = item["partition"]
            wanted_hash = item["sha256"]
            wanted_size = item["bytes"]
        except (KeyError, TypeError) as error:
            raise ValueError("malformed restore manifest payload") from error
        if (not isinstance(filename, str) or Path(filename).name != filename or
                not isinstance(wanted_hash, str) or len(wanted_hash) != 64 or
                not isinstance(wanted_size, int) or wanted_size <= 0):
            raise ValueError("unsafe restore manifest payload")
        actual.add((role, source, filename, partition))
        path = regular(root / filename, f"payload {filename}")
        if path.parent != root:
            raise ValueError(f"payload escaped restore directory: {filename}")
        if path.stat().st_size != wanted_size or sha256(path) != wanted_hash:
            raise ValueError(f"prepared payload changed: {filename}")
        if partition is not None:
            flash.append((partition, path))
    if actual != expected_payloads():
        raise ValueError("restore manifest does not contain the exact payload set")
    if len(flash) != 40 or len({part for part, _ in flash}) != 40:
        raise ValueError("restore must target exactly 40 unique partitions")
    pit = regular(root / prepare_factory_restore.PIT_NAME, "factory PIT")
    if sha256(pit) != prepare_factory_restore.PIT_SHA256:
        raise ValueError("factory PIT changed")
    return pit, flash


def validate_heimdall(path: Path, wanted_hash: str) -> Path:
    path = regular(path, "Heimdall binary")
    if sha256(path) != wanted_hash.lower():
        raise ValueError("Heimdall binary SHA-256 mismatch")
    result = subprocess.run(
        [str(path), "version"], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if "v2.2.2" not in result.stdout:
        raise ValueError("unexpected Heimdall version")
    return path


def pit_structure(heimdall: Path, pit: Path) -> str:
    result = subprocess.run(
        [str(heimdall), "print-pit", "--file", str(pit), "--stdout-errors"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    marker = "--- PIT Header ---"
    if marker not in result.stdout:
        raise ValueError("Heimdall could not parse PIT structure")
    structure = result.stdout[result.stdout.index(marker):].strip()
    for required in ("Entry Count: 91", "CPU/bootloader tag: SM7325",
                     "Logic unit count: 6", "Partition Name: BOOT",
                     "Partition Name: SUPER", "Partition Name: USERDATA"):
        if required not in structure:
            raise ValueError(f"PIT structure is missing {required}")
    return structure


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def flash(
        manifest: Path, heimdall: Path, heimdall_hash: str,
        authorization: str, check_only: bool, resume_download: bool,
        payload_only: bool) -> None:
    pit, payloads = validate_manifest(manifest)
    heimdall = validate_heimdall(heimdall, heimdall_hash)
    print("FACTORY_RESTORE_FILES_VERIFIED: 40 payloads; wiping CSC; stock PIT")
    if check_only:
        print("FACTORY_RESTORE_LOCAL_READY_NO_DEVICE_WRITE")
        return
    if authorization != AUTHORIZATION:
        raise ValueError(f"--authorize must equal: {AUTHORIZATION}")

    run([str(heimdall), "detect", "--stdout-errors"])
    descriptor, live_name = tempfile.mkstemp(
        prefix="live-pit-before-restore-", suffix=".bin", dir=pit.parent)
    os.close(descriptor)
    live_pit = Path(live_name)
    os.chmod(live_pit, 0o600)
    try:
        download = [str(heimdall), "download-pit"]
        if resume_download:
            download.append("--resume")
        download.extend(["--output", str(live_pit), "--no-reboot",
                         "--stdout-errors"])
        run(download)
        if pit_structure(heimdall, live_pit) != pit_structure(heimdall, pit):
            raise ValueError(
                "connected device PIT structure is not the exact SM-T630 layout; "
                "no flash was attempted")
        saved = pit.parent / "live-pit-before-restore.bin"
        if saved.exists() or saved.is_symlink():
            saved = regular(saved, "previously saved live PIT")
            if sha256(saved) != sha256(live_pit):
                raise ValueError("live PIT changed since the earlier pre-flash read")
            live_pit.unlink()
        else:
            live_pit.rename(saved)

        command = [str(heimdall), "flash", "--resume"]
        if not payload_only:
            command.extend(["--repartition", "--pit", str(pit)])
        for partition, path in payloads:
            command.extend([f"--{partition}", str(path)])
        command.append("--stdout-errors")
        mode = ("40 Samsung payloads on a separately restored stock GPT" if
                payload_only else "repartition plus 40 Samsung payloads")
        print(f"FACTORY_RESTORE_STARTING: {mode}", flush=True)
        run(command)
        print("FACTORY_RESTORE_FLASH_SUCCEEDED: tablet reboot requested")
    finally:
        if live_pit.exists():
            live_pit.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--heimdall", required=True, type=Path)
    parser.add_argument("--heimdall-sha256", required=True)
    parser.add_argument("--check", action="store_true",
                        help="verify local inputs without contacting the tablet")
    parser.add_argument("--flash", action="store_true",
                        help="perform the destructive factory restore")
    parser.add_argument("--authorize", default="")
    parser.add_argument(
        "--resume-download", action="store_true",
        help="resume a Download Mode session left open by an earlier PIT read")
    parser.add_argument(
        "--payload-only", action="store_true",
        help="do not resend PIT; valid only after separately restoring the exact stock GPT")
    args = parser.parse_args()
    if args.check == args.flash:
        parser.error("choose exactly one of --check or --flash")
    try:
        if args.check and args.resume_download:
            parser.error("--resume-download is only valid with --flash")
        if args.check and args.payload_only:
            parser.error("--payload-only is only valid with --flash")
        flash(args.manifest.expanduser(), args.heimdall.expanduser(),
              args.heimdall_sha256, args.authorize, args.check,
              args.resume_download, args.payload_only)
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"FACTORY_RESTORE_REFUSED: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
