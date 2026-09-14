#!/usr/bin/env python3
"""Validate and optionally install the exact SM-T630 package set offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

from audit_release_root import audit


OFFLINE_MARKER = "SM-T630 OFFLINE RELEASE ROOT\n"
INSTALL_ID = "SM-T630-T630XXSBDZE3-Ubuntu-v1"
EXPECTED = {
    "t630-first-boot_0.1.1_all.deb": (
        "t630-first-boot", "0.1.1",
        "a18e0a100b006b8f9afd82c3ff28501a27c37ee1e0680c80efca1699f9e5d9b2"),
    "t630-desktop-runtime_0.1.1_all.deb": (
        "t630-desktop-runtime", "0.1.1",
        "ebf85f4fad2602670f400f80eb5b323c4b44fbaadb4b22c0fd8dfd5a697adc52"),
    "t630-hardware-runtime_0.1.2_all.deb": (
        "t630-hardware-runtime", "0.1.2",
        "821f7dec058a73149e2704f3ea8179058e009a425df562a09aafa16b03a6b632"),
    "t630-boot-runtime_0.1.0_all.deb": (
        "t630-boot-runtime", "0.1.0",
        "7ec7c61eab7f12460bcf25d8bb3cfd528107a43742fd4dfca4abc1ed06a9dc1d"),
    "t630-polkit-runtime_0.1.0_arm64.deb": (
        "t630-polkit-runtime", "0.1.0",
        "baa7fbcd300895bd6754eac6dec95061f9f99a8a56c8f5a4d5ac059193f886da"),
    "t630-login-runtime_0.1.0_arm64.deb": (
        "t630-login-runtime", "0.1.0",
        "edfc0b58325acc95c1e4dd25befd53bdaec30faf795dfb8a37d06fb4de6aa23e"),
    "t630-camera-runtime_0.1.2_arm64.deb": (
        "t630-camera-runtime", "0.1.2",
        "ab475d8df972e23c02d3d92dec380c37ece3e3d88d52dfdcbba24ac6b3ae6d1d"),
    "t630-native-userspace_0.1.0_arm64.deb": (
        "t630-native-userspace", "0.1.0",
        "b6e9dffc3ce27278084a0fbc9022189e289eaf3c06fdcc5db1e9877a6dfed6ff"),
    "t630-pd-mapper_0.1.0_arm64.deb": (
        "t630-pd-mapper", "0.1.0",
        "f0d06b0b6be7fe94f2c1b868e3a0c4856e89216768cbb2bbe43a8e0e381a6960"),
    "libssc_0.4.4-t6303_arm64.deb": (
        "libssc", "0.4.4-t6303",
        "3522d445c183452e47d789211a9339669285acd6f0d54dcfb40553cd122c8fec"),
    "hexagonrpcd_0.4.0-t6303_arm64.deb": (
        "hexagonrpcd", "0.4.0-t6303",
        "0b97140e1b803f0362da17b5e1bf1ed96295f68accd04fffdc00d15c4ffd2db9"),
    "iio-sensor-proxy_3.9-t6303_arm64.deb": (
        "iio-sensor-proxy", "3.9-t6303",
        "1ffcc6881cf458e400d2efac744ba38564415a1f416e4c2ed9ef37fa0354bd29"),
    "t630-stock-assets_1.0.1+dze3_arm64.deb": (
        "t630-stock-assets", "1.0.1+dze3",
        "934f3c361fedc806eef90b4b92a6f93c906492b6b29339cb4e2cf85c0c7b461e"),
    "t630-release-base_0.1.7_arm64.deb": (
        "t630-release-base", "0.1.7",
        "d2ad6b14f92b38c7aeba292e490c17a64228e66df8b920ee17165bd4d6e992b0"),
}
INSTALL_ORDER = tuple(name for name in EXPECTED if not name.startswith("t630-release-base_"))
META_PACKAGE = "t630-release-base_0.1.7_arm64.deb"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def package_field(path: Path, field: str) -> str:
    return subprocess.check_output(
        ["dpkg-deb", "-f", path, field], text=True).strip()


def validate_packages(directory: Path) -> dict:
    if directory.is_symlink():
        raise ValueError("package source must be a real directory")
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("package source must be a real directory")
    records = []
    for filename, (package, version, wanted) in EXPECTED.items():
        path = directory / filename
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or unsafe release package: {filename}")
        actual = digest(path)
        if actual != wanted:
            raise ValueError(f"release package checksum mismatch: {filename}")
        if package_field(path, "Package") != package:
            raise ValueError(f"release package name mismatch: {filename}")
        if package_field(path, "Version") != version:
            raise ValueError(f"release package version mismatch: {filename}")
        records.append({"file": filename, "package": package,
                        "version": version, "sha256": actual})
    private = directory / "t630-stock-assets_1.0.1+dze3_arm64.deb"
    if stat.S_IMODE(private.stat().st_mode) & 0o077:
        raise ValueError("private stock package must not be group/world accessible")
    return {"device": "Samsung SM-T630", "baseline": "T630XXSBDZE3",
            "packages": records}


def validate_root(root: Path) -> Path:
    if root.is_symlink():
        raise ValueError("refusing live or unsafe release root")
    root = root.resolve(strict=True)
    if root == Path("/") or not root.is_dir():
        raise ValueError("refusing live or unsafe release root")
    marker = root / ".t630-offline-root"
    if (not marker.is_file() or marker.is_symlink() or
            marker.read_text(encoding="utf-8") != OFFLINE_MARKER):
        raise ValueError("offline root marker is absent or invalid")
    os_release = (root / "etc/os-release").read_text(encoding="utf-8")
    if "ID=ubuntu\n" not in os_release or 'VERSION_ID="24.04"\n' not in os_release:
        raise ValueError("offline root is not Ubuntu 24.04")
    failures = audit(root)
    if failures:
        raise ValueError("release-root identity audit failed: " + "; ".join(failures))
    return root


def install(root: Path, packages: Path) -> None:
    if os.geteuid() != 0:
        raise PermissionError("offline package installation requires root")
    root = validate_root(root)
    package_paths = [str(packages / name) for name in INSTALL_ORDER]
    subprocess.run(["dpkg", f"--root={root}", "--unpack", *package_paths], check=True)
    subprocess.run(["dpkg", f"--root={root}", "--configure", "-a"], check=True)
    subprocess.run(["dpkg", f"--root={root}", "--install",
                    str(packages / META_PACKAGE)], check=True)
    if (root / "etc/t630-install-id").read_text().strip() != INSTALL_ID:
        raise RuntimeError("installed device marker mismatch")
    failures = audit(root)
    if failures:
        raise RuntimeError("post-install identity audit failed: " + "; ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_directory", type=Path)
    parser.add_argument("--root", type=Path,
                        help="offline Ubuntu 24.04 root marked .t630-offline-root")
    parser.add_argument("--apply", action="store_true",
                        help="install after all checks; default is validation only")
    args = parser.parse_args()
    record = validate_packages(args.package_directory)
    if args.root is not None:
        validate_root(args.root)
    if args.apply:
        if args.root is None:
            parser.error("--apply requires --root")
        install(args.root, args.package_directory.resolve())
        record["installed_root"] = str(args.root.resolve())
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
