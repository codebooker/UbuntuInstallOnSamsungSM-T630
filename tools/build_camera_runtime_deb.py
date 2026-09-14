#!/usr/bin/env python3
"""Package the redistributable SM-T630 camera compatibility runtime."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-camera-runtime"
VERSION = "0.1.3"
SOURCE_FILES = {
    "etc/sudoers.d/t630-camera": ("ubuntu/t630-camera-sudoers", 0o440),
    "usr/local/bin/t630-camera-app": ("ubuntu/t630-camera-app", 0o755),
    "usr/local/bin/t630-camera-color": ("ubuntu/t630-camera-color.py", 0o755),
    "usr/local/sbin/t630-camera-bridge": ("ubuntu/t630-camera-bridge", 0o755),
    "usr/local/sbin/t630-camera-control": ("ubuntu/t630-camera-control", 0o755),
    "usr/local/sbin/t630-camera-mounts": ("camera/t630-camera-mounts.sh", 0o755),
    "usr/local/sbin/t630-camera-stack": ("camera/t630-camera-stack.sh", 0o755),
    "usr/local/sbin/t630-android-log-capture": (
        "ubuntu/t630-android-log-capture.py", 0o755),
    "usr/local/share/t630/t630-camera-nodes.py": (
        "ubuntu/t630-camera-nodes.py", 0o755),
    "usr/local/share/t630/test-t630-camera-frame.py": (
        "ubuntu/test-t630-camera-frame.py", 0o755),
    "usr/local/share/t630/camera-templates/ld.config.txt": (
        "ubuntu/t630-android-ld.config.txt", 0o644),
    "usr/local/share/t630/camera-templates/vendor-manifest.xml": (
        "ubuntu/t630-vendor-manifest.xml", 0o644),
    "usr/share/applications/t630-camera.desktop": (
        "ubuntu/t630-camera.desktop", 0o644),
    "usr/share/applications/t630-rear-camera.desktop": (
        "ubuntu/t630-rear-camera.desktop", 0o644),
    "usr/share/applications/t630-camera-color.desktop": (
        "ubuntu/t630-camera-color.desktop", 0o644),
    "usr/share/doc/t630-camera-runtime/copyright": ("LICENSE", 0o644),
}
NATIVE_FILES = {
    "usr/local/lib/t630-android-property-seed.so": "t630-android-property-seed.so",
    "usr/local/libexec/t630-binder-placeholder": "t630-binder-placeholder",
    "usr/local/libexec/t630-camera-capture": "t630-camera-capture",
    "usr/local/sbin/t630-sensorservice-hidl": "t630-sensorservice-hidl",
    "usr/local/sbin/t630-yuv-tune": "t630-yuv-tune",
}


def arm64_elf(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe native artifact: {path.name}")
    data = path.read_bytes()
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError(f"not a little-endian ELF64 artifact: {path.name}")
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    if elf_type not in (2, 3) or machine != 183:
        raise ValueError(f"not an ARM64 executable/shared artifact: {path.name}")
    return data


def build(staging: Path, output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    staging = staging.resolve(strict=True)
    payload: dict[str, tuple[bytes, int]] = {}
    for destination, (source, mode) in SOURCE_FILES.items():
        path = ROOT / source
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or unsafe source: {source}")
        data = path.read_bytes()
        if source != "LICENSE":
            data.decode("utf-8")
        payload[destination] = (data, mode)
    for destination, source in NATIVE_FILES.items():
        payload[destination] = (arm64_elf(staging / source), 0o755)

    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: arm64
Maintainer: SM-T630 Ubuntu Port contributors
Depends: t630-first-boot (= 0.1.1), t630-desktop-runtime (= 0.1.1), t630-hardware-runtime (= 0.1.2), t630-stock-assets (= 1.0.1+dze3), python3, python3-gi, gir1.2-gtk-4.0, sudo, dmsetup, util-linux, pipewire, gstreamer1.0-tools, gstreamer1.0-plugins-base, gstreamer1.0-plugins-good, gnome-snapshot
Section: admin
Priority: optional
Description: camera compatibility runtime for Ubuntu on Samsung SM-T630
 Contains redistributable launchers and source-built ARM64 helpers. Proprietary
 Samsung/Qualcomm libraries, calibration, firmware images and user data are not
 included and must be reconstructed locally from exact T630XXSBDZE3 firmware.
""".encode()
    control_archive = tar_bytes(
        {"control": (control, 0o644), "md5sums": (md5sums, 0o644)}, epoch)
    package = b"!<arch>\n"
    package += ar_member("debian-binary", b"2.0\n", epoch)
    package += ar_member("control.tar.xz", control_archive, epoch)
    package += ar_member("data.tar.xz", tar_bytes(payload, epoch), epoch)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary.write(package)
        temporary_path = Path(temporary.name)
    temporary_path.chmod(0o644)
    temporary_path.replace(output)
    return hashlib.sha256(package).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_arm64.deb")
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")))
    args = parser.parse_args()
    digest = build(args.staging, args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
