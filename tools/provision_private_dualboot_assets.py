#!/usr/bin/env python3
"""Install private BOOT-switch assets into an offline SM-T630 release root."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil

from assemble_release_root import validate_root


BOOT_BYTES = 100663296
UBUNTU_BOOT_SHA256 = "fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f"
STOCK_ANDROID_BOOT_SHA256 = "79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796"
AUTHORIZATION = "SWITCH SM-T630 FROM ACCEPTED UBUNTU TO ACCEPTED NATIVE ANDROID\n"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def checked_boot(path: Path, label: str) -> tuple[Path, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    path = path.resolve(strict=True)
    if path.stat().st_size != BOOT_BYTES:
        raise ValueError(f"{label} is not an exact BOOT-sized image")
    return path, digest(path)


def provision(root: Path, android_boot: Path, ubuntu_boot: Path) -> dict:
    if os.geteuid() != 0:
        raise PermissionError("root is required to preserve private ownership")
    root = validate_root(root)
    android_boot, android_hash = checked_boot(android_boot, "Android BOOT")
    ubuntu_boot, ubuntu_hash = checked_boot(ubuntu_boot, "Ubuntu BOOT")
    if ubuntu_hash != UBUNTU_BOOT_SHA256:
        raise ValueError("Ubuntu BOOT is not the accepted module-compatible image")
    if android_hash == STOCK_ANDROID_BOOT_SHA256:
        raise ValueError("Android BOOT is stock and would not preserve the rooted switch service")

    artifact = root / "opt/t630/artifacts/native-android-stock"
    if artifact.exists() or artifact.is_symlink():
        raise ValueError("refusing to overwrite existing private dual-boot assets")
    artifact.mkdir(parents=True, mode=0o700)
    try:
        files = {
            "boot.img": android_boot,
            "ubuntu-dual-layout.transaction-rollback.img": ubuntu_boot,
        }
        for name, source in files.items():
            destination = artifact / name
            shutil.copyfile(source, destination)
            destination.chmod(0o400)
        (artifact / "boot.sha256").write_text(android_hash + "\n", encoding="ascii")
        temporary = artifact / ".AUTHORIZE-NATIVE-ANDROID-SWITCH.tmp"
        temporary.write_text(AUTHORIZATION, encoding="ascii")
        authorization = artifact / "AUTHORIZE-NATIVE-ANDROID-SWITCH"
        temporary.replace(authorization)
        for path in (artifact / "boot.sha256", authorization):
            path.chmod(0o400)
        if digest(artifact / "boot.img") != android_hash:
            raise ValueError("Android BOOT copy verification failed")
        if digest(artifact / "ubuntu-dual-layout.transaction-rollback.img") != ubuntu_hash:
            raise ValueError("Ubuntu BOOT copy verification failed")
    except Exception:
        shutil.rmtree(artifact, ignore_errors=True)
        raise
    return {
        "status": "PRIVATE_DUALBOOT_ASSETS_PROVISIONED_NO_PARTITION_WRITE",
        "android_boot_sha256": android_hash,
        "ubuntu_boot_sha256": ubuntu_hash,
        "acceptance_marker_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("android_boot", type=Path)
    parser.add_argument("ubuntu_boot", type=Path)
    args = parser.parse_args()
    print(provision(args.root, args.android_boot, args.ubuntu_boot))


if __name__ == "__main__":
    main()
