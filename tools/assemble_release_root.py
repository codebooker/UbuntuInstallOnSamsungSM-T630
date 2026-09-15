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
        "3b3adf74477f0402e30d3d443dcd49068eb2bf139afa83a2f4c4e346bb18a14e"),
    "t630-desktop-runtime_0.1.4_all.deb": (
        "t630-desktop-runtime", "0.1.4",
        "daddaa1a4a661b359a391aa119c2ca5a8278445d41972350b2f8622fc87482f8"),
    "t630-hardware-runtime_0.1.5_all.deb": (
        "t630-hardware-runtime", "0.1.5",
        "01dc907cd4f3879032f70c6ccc702e731bba57cdb3d1d208642ee07d3ffbd8fd"),
    "t630-boot-runtime_0.1.0_all.deb": (
        "t630-boot-runtime", "0.1.0",
        "70c75d8b0e68c48fbc8366bbe0432df0e4a1acde99cde096ae05902f51bdde9e"),
    "t630-polkit-runtime_0.1.0_arm64.deb": (
        "t630-polkit-runtime", "0.1.0",
        "baa7fbcd300895bd6754eac6dec95061f9f99a8a56c8f5a4d5ac059193f886da"),
    "t630-login-runtime_0.1.0_arm64.deb": (
        "t630-login-runtime", "0.1.0",
        "edfc0b58325acc95c1e4dd25befd53bdaec30faf795dfb8a37d06fb4de6aa23e"),
    "t630-camera-runtime_0.1.4_arm64.deb": (
        "t630-camera-runtime", "0.1.4",
        "71d8544ec48575919a0f079a67da89b1b3ca92abdbd1db0fc967f60089bc5bcb"),
    "t630-native-userspace_0.1.0_arm64.deb": (
        "t630-native-userspace", "0.1.0",
        "b6e9dffc3ce27278084a0fbc9022189e289eaf3c06fdcc5db1e9877a6dfed6ff"),
    "t630-pd-mapper_0.1.0_arm64.deb": (
        "t630-pd-mapper", "0.1.0",
        "9236ef5c8a6393d957895a3b153636cf97b1fec682701f4639292560a5365d55"),
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
    "t630-release-base_0.1.12_arm64.deb": (
        "t630-release-base", "0.1.12",
        "d230d7c43c7c1cb50d5a3dca384971d029b946c3295bca81b2891d558e2e5362"),
}
INSTALL_ORDER = tuple(name for name in EXPECTED if not name.startswith("t630-release-base_"))
META_PACKAGE = "t630-release-base_0.1.12_arm64.deb"


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
