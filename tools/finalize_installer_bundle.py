#!/usr/bin/env python3
"""Verify and seal the private SM-T630 rootfs/BOOT installer input directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


EXPECTED_BOOT_SHA256 = "a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28"
EXPECTED_KERNEL_SHA256 = "7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6"
EXPECTED_BOOT_BYTES = 100663296
ROOT_UUID = "64de8544-53ea-4fdc-8946-d6b07e238630"
INPUTS = (
    "t630-release-rootfs.tar.gz",
    "t630-release-rootfs.tar.gz.manifest.json",
    "t630-installer-runtime.tar.gz",
    "t630-installer-runtime.tar.gz.manifest.json",
    "boot/boot.img",
    "boot/manifest.json",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def safe_file(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing or unsafe installer input: {relative}")
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"installer input escapes work directory: {relative}")
    return resolved


def read_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid installer manifest: {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"invalid installer manifest: {path.name}")
    return value


def validate(work: Path) -> dict:
    if work.is_symlink() or not work.is_dir():
        raise ValueError("installer work path must be a real directory")
    work = work.resolve(strict=True)
    paths = {name: safe_file(work, name) for name in INPUTS}
    rootfs = paths[INPUTS[0]]
    root_record = read_manifest(paths[INPUTS[1]])
    if root_record.get("status") != "LOCAL_PRIVATE_INSTALLER_INPUT_DO_NOT_REDISTRIBUTE":
        raise ValueError("rootfs manifest does not mark a private local input")
    if root_record.get("model") != "SM-T630" or root_record.get("stock_build") != "T630XXSBDZE3":
        raise ValueError("rootfs manifest baseline mismatch")
    if root_record.get("archive") != rootfs.name:
        raise ValueError("rootfs manifest filename mismatch")
    root_hash = digest(rootfs)
    if (root_record.get("archive_sha256") != root_hash or
            root_record.get("archive_bytes") != rootfs.stat().st_size):
        raise ValueError("rootfs manifest content mismatch")
    if root_record.get("contains_proprietary_stock_assets") is not True:
        raise ValueError("rootfs proprietary boundary is not declared")
    if (root_record.get("contains_human_account") is not False or
            root_record.get("contains_network_credentials") is not False):
        raise ValueError("rootfs identity boundary is not clean")

    runtime = paths[INPUTS[2]]
    runtime_record = read_manifest(paths[INPUTS[3]])
    if runtime_record.get("status") != "PRIVATE_INSTALLER_RUNTIME_ARM64_NO_DEVICE_WRITE":
        raise ValueError("installer runtime manifest status mismatch")
    if (runtime_record.get("model") != "SM-T630" or
            runtime_record.get("stock_build") != "T630XXSBDZE3" or
            runtime_record.get("archive") != runtime.name or
            runtime_record.get("archive_bytes") != runtime.stat().st_size or
            runtime_record.get("archive_sha256") != digest(runtime)):
        raise ValueError("installer runtime manifest content mismatch")

    boot = paths[INPUTS[4]]
    boot_record = read_manifest(paths[INPUTS[5]])
    if (boot_record.get("model") != "SM-T630" or
            boot_record.get("stock_build") != "T630XXSBDZE3" or
            boot_record.get("root_uuid") != ROOT_UUID):
        raise ValueError("BOOT manifest baseline mismatch")
    boot_hash = digest(boot)
    if (boot.stat().st_size != EXPECTED_BOOT_BYTES or
            boot_record.get("boot_bytes") != EXPECTED_BOOT_BYTES or
            boot_hash != EXPECTED_BOOT_SHA256 or
            boot_record.get("boot_sha256") != EXPECTED_BOOT_SHA256):
        raise ValueError("BOOT is not the physically accepted v12 image")
    if boot_record.get("kernel_sha256") != EXPECTED_KERNEL_SHA256:
        raise ValueError("BOOT kernel is not the accepted module-compatible build")

    files = []
    for name in INPUTS:
        path = paths[name]
        files.append({"path": name, "bytes": path.stat().st_size,
                      "sha256": digest(path)})
    return {
        "status": "PRIVATE_INSTALLER_BUNDLE_SEALED_NOT_DEVICE_WRITE_AUTHORIZATION",
        "model": "SM-T630",
        "stock_build": "T630XXSBDZE3",
        "root_uuid": ROOT_UUID,
        "files": files,
        "contains_proprietary_stock_assets": True,
        "device_writes": "none",
        "next_gate": "recovery transport must verify SHA256SUMS before any format",
    }


def private_write(path: Path, data: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def finalize(work: Path) -> dict:
    work = work.expanduser().resolve(strict=True)
    bundle = work / "installer-bundle.json"
    sums = work / "SHA256SUMS"
    if bundle.exists() or bundle.is_symlink() or sums.exists() or sums.is_symlink():
        raise ValueError("refusing to overwrite a sealed bundle")
    record = validate(work)
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    try:
        private_write(bundle, rendered)
        lines = "".join(f"{entry['sha256']}  {entry['path']}\n"
                        for entry in record["files"])
        lines += f"{digest(bundle)}  {bundle.name}\n"
        private_write(sums, lines)
    except Exception:
        bundle.unlink(missing_ok=True)
        sums.unlink(missing_ok=True)
        raise
    # Re-read the sealed inputs and then include their hashes in returned output.
    validate(work)
    record["seal_files"] = [
        {"path": bundle.name, "bytes": bundle.stat().st_size,
         "sha256": digest(bundle)},
        {"path": sums.name, "bytes": sums.stat().st_size,
         "sha256": digest(sums)},
    ]
    return record


def verify_sealed(work: Path) -> dict:
    work = work.expanduser().resolve(strict=True)
    bundle = safe_file(work, "installer-bundle.json")
    sums = safe_file(work, "SHA256SUMS")
    record = validate(work)
    sealed_record = read_manifest(bundle)
    if sealed_record != record:
        raise ValueError("sealed bundle manifest differs from current inputs")
    wanted = "".join(f"{entry['sha256']}  {entry['path']}\n"
                     for entry in record["files"])
    wanted += f"{digest(bundle)}  {bundle.name}\n"
    if sums.read_text(encoding="ascii") != wanted:
        raise ValueError("sealed SHA256SUMS differs from current inputs")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_directory", type=Path)
    parser.add_argument("--verify", action="store_true",
                        help="verify an existing seal instead of creating it")
    args = parser.parse_args()
    action = verify_sealed if args.verify else finalize
    print(json.dumps(action(args.work_directory), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
