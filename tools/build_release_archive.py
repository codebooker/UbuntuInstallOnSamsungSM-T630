#!/usr/bin/env python3
"""Create a private, identity-clean SM-T630 rootfs archive for local install."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import tarfile
from typing import Dict, Tuple

from assemble_release_root import EXPECTED, INSTALL_ID, validate_root


SOURCE_DATE_EPOCH = 1700000000


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def dpkg_status(root: Path) -> Dict[str, Dict[str, str]]:
    path = root / "var/lib/dpkg/status"
    if not path.is_file() or path.is_symlink():
        raise ValueError("offline root has no safe dpkg status database")
    packages: Dict[str, Dict[str, str]] = {}
    for paragraph in path.read_text(encoding="utf-8").split("\n\n"):
        fields: Dict[str, str] = {}
        for line in paragraph.splitlines():
            if not line or line[0].isspace() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key] = value.strip()
        if "Package" in fields:
            packages[fields["Package"]] = fields
    return packages


def validate_installed_root(root: Path) -> Tuple[Path, Dict[str, str]]:
    root = validate_root(root)
    marker = root / "etc/t630-install-id"
    if (not marker.is_file() or marker.is_symlink() or
            marker.read_text(encoding="utf-8").strip() != INSTALL_ID):
        raise ValueError("installed device marker mismatch")
    status = dpkg_status(root)
    versions: Dict[str, str] = {}
    for package, version, _wanted in EXPECTED.values():
        fields = status.get(package, {})
        if fields.get("Status") != "install ok installed":
            raise ValueError(f"release package is not installed: {package}")
        if fields.get("Version") != version:
            raise ValueError(f"release package version mismatch: {package}")
        versions[package] = version
    return root, versions


def check_tools() -> Tuple[str, str]:
    tar = shutil.which("tar")
    gzip = shutil.which("gzip")
    if not tar or not gzip:
        raise RuntimeError("GNU tar and gzip are required")
    version = subprocess.check_output([tar, "--version"], text=True)
    if "GNU tar" not in version.splitlines()[0]:
        raise RuntimeError("GNU tar is required to preserve ACLs and xattrs")
    return tar, gzip


def reject_mounts(root: Path) -> None:
    prefix = str(root).rstrip("/") + "/"
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = line.split(" - ", 1)[0].split()
        if len(fields) < 5:
            raise ValueError("cannot parse mount table")
        mountpoint = re.sub(
            r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), fields[4])
        if mountpoint == str(root) or mountpoint.startswith(prefix):
            raise ValueError(f"offline root contains a live mount: {mountpoint}")


def archive_members(archive: Path) -> int:
    count = 0
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("release archive contains an unsafe path")
            count += 1
    if count == 0:
        raise ValueError("release archive is empty")
    return count


def build(root: Path, output: Path) -> dict:
    if os.geteuid() != 0:
        raise PermissionError("root is required to preserve numeric ownership")
    root, versions = validate_installed_root(root)
    reject_mounts(root)
    output = output.expanduser().resolve()
    manifest_path = output.with_name(output.name + ".manifest.json")
    if output.exists() or output.is_symlink() or manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError("refusing to overwrite a release archive or manifest")
    output.parent.mkdir(parents=True, exist_ok=True)
    tar, gzip = check_tools()
    temporary = output.with_name(output.name + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("temporary archive path already exists")
    tar_command = [
        tar, "--create", "--file=-", f"--directory={root}",
        "--numeric-owner", "--acls", "--xattrs", "--xattrs-include=*",
        "--one-file-system", "--sort=name",
        f"--mtime=@{SOURCE_DATE_EPOCH}",
        "--pax-option=delete=atime,delete=ctime", ".",
    ]
    try:
        with os.fdopen(
                os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                "wb") as target:
            producer = subprocess.Popen(tar_command, stdout=subprocess.PIPE)
            assert producer.stdout is not None
            compressor = subprocess.Popen([gzip, "-n", "-9"], stdin=producer.stdout,
                                          stdout=target)
            producer.stdout.close()
            gzip_result = compressor.wait()
            tar_result = producer.wait()
            if tar_result or gzip_result:
                raise subprocess.CalledProcessError(
                    tar_result or gzip_result, tar_command)
            target.flush()
            os.fsync(target.fileno())
        temporary.rename(output)
        member_count = archive_members(output)
        # The build must not cause identity state to appear in the source tree.
        validate_installed_root(root)
        reject_mounts(root)
        record = {
            "status": "LOCAL_PRIVATE_INSTALLER_INPUT_DO_NOT_REDISTRIBUTE",
            "model": "SM-T630",
            "stock_build": "T630XXSBDZE3",
            "archive": output.name,
            "archive_bytes": output.stat().st_size,
            "archive_sha256": digest(output),
            "archive_members": member_count,
            "source_date_epoch": SOURCE_DATE_EPOCH,
            "release_packages": dict(sorted(versions.items())),
            "contains_proprietary_stock_assets": True,
            "contains_human_account": False,
            "contains_network_credentials": False,
            "device_writes": "none; this builder only creates local artifacts",
        }
        with os.fdopen(
                os.open(manifest_path,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return record
    except Exception:
        temporary.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path,
                        help="completed, identity-clean offline release root")
    parser.add_argument("output", type=Path,
                        help="new .tar.gz path; mode 0600 and never redistributable")
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
