#!/usr/bin/env python3
"""Build the private ARM64 mkfs/e2fsck/GNU-tar recovery runtime."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import tarfile
from typing import Dict, Set

from build_release_archive import validate_installed_root


SOURCE_DATE_EPOCH = 1700000000
BINARIES = ("/usr/sbin/mke2fs", "/usr/sbin/e2fsck", "/usr/bin/tar",
            "/usr/bin/dpkg-query")
CONFIGS = ("/etc/mke2fs.conf",)
LIBRARY = re.compile(r"(?:=>\s+)?(/[^\s()]+)")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def safe_source(root: Path, absolute: str) -> Path:
    pure = PurePosixPath(absolute)
    if not pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe runtime source path: {absolute}")
    candidate = root / str(pure).lstrip("/")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"runtime source escapes root: {absolute}") from error
    if not resolved.is_file():
        raise ValueError(f"runtime source is not a file: {absolute}")
    return resolved


def arm64_elf(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(64)
    if (header[:6] != b"\x7fELF\x02\x01" or len(header) < 20 or
            struct.unpack_from("<H", header, 18)[0] != 183):
        raise ValueError(f"runtime binary is not ARM64 ELF64: {path}")


def ldd_paths(output: str) -> Set[str]:
    result: Set[str] = set()
    for line in output.splitlines():
        if "not found" in line:
            raise ValueError("installer runtime has an unresolved library")
        match = LIBRARY.search(line)
        if match:
            result.add(match.group(1))
    if not any("ld-linux-aarch64" in path for path in result):
        raise ValueError("ARM64 runtime loader was not reported by ldd")
    return result


def runtime_files(root: Path) -> Dict[str, Path]:
    files = {path: safe_source(root, path) for path in BINARIES + CONFIGS}
    for binary in BINARIES:
        source = files[binary]
        arm64_elf(source)
        output = subprocess.check_output(
            ["chroot", root, "/usr/bin/ldd", binary], text=True,
            stderr=subprocess.STDOUT)
        for library in ldd_paths(output):
            files[library] = safe_source(root, library)
    return files


def add_directory(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    info.mtime = SOURCE_DATE_EPOCH
    archive.addfile(info)


def write_archive(files: Dict[str, Path], output: Path) -> None:
    directories: Set[str] = set()
    for absolute in files:
        parent = PurePosixPath(absolute).parent
        while str(parent) not in ("/", "."):
            directories.add(str(parent).lstrip("/") + "/")
            parent = parent.parent
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw,
                           compresslevel=9, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|",
                              format=tarfile.PAX_FORMAT) as archive:
                for directory in sorted(directories):
                    add_directory(archive, directory)
                for absolute, source in sorted(files.items()):
                    info = tarfile.TarInfo(absolute.lstrip("/"))
                    info.size = source.stat().st_size
                    info.mode = stat.S_IMODE(source.stat().st_mode)
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = SOURCE_DATE_EPOCH
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
        raw.flush()
        os.fsync(raw.fileno())


def private_json(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def build(root: Path, output: Path) -> dict:
    if os.geteuid() != 0:
        raise PermissionError("root is required to inspect the ARM64 chroot")
    root, _versions = validate_installed_root(root)
    output = output.expanduser().resolve()
    manifest = output.with_name(output.name + ".manifest.json")
    if output.exists() or output.is_symlink() or manifest.exists() or manifest.is_symlink():
        raise ValueError("refusing to overwrite installer runtime output")
    output.parent.mkdir(parents=True, exist_ok=True)
    files = runtime_files(root)
    try:
        write_archive(files, output)
        record = {
            "status": "PRIVATE_INSTALLER_RUNTIME_ARM64_NO_DEVICE_WRITE",
            "model": "SM-T630",
            "stock_build": "T630XXSBDZE3",
            "archive": output.name,
            "archive_bytes": output.stat().st_size,
            "archive_sha256": digest(output),
            "files": [
                {"path": path, "bytes": source.stat().st_size,
                 "sha256": digest(source)}
                for path, source in sorted(files.items())
            ],
            "device_writes": "none",
        }
        private_json(manifest, record)
        return record
    except Exception:
        output.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
