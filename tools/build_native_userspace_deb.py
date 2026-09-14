#!/usr/bin/env python3
"""Package reproducibly built SM-T630 native userspace binaries."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-native-userspace"
VERSION = "0.1.0"
FILES = {
    "usr/local/lib/t630-cogl-sync.so": "t630-cogl-sync.so",
    "usr/local/lib/t630-drm-compat.so": "t630-drm-compat.so",
    "usr/local/lib/t630-xput-image.so": "t630-xput-image.so",
    "usr/local/lib/im-t630-wayland.so": "im-t630-wayland.so",
    "usr/local/libexec/t630-capture": "t630-capture",
    "usr/lib/aarch64-linux-gnu/weston/t630-rotation.so": "t630-rotation.so",
}
POSTINST = b"""#!/bin/sh
set -e
query=/usr/lib/aarch64-linux-gnu/libgtk-3-0t64/gtk-query-immodules-3.0
test -x "$query"
"$query" /usr/local/lib/im-t630-wayland.so > /usr/local/share/t630/gtk-immodules.cache
"""


def validate_arm64_elf(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe native artifact: {path.name}")
    data = path.read_bytes()
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError(f"not a little-endian ELF64 artifact: {path.name}")
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    if elf_type != 3 or machine != 183:
        raise ValueError(f"not an ARM64 PIE/shared artifact: {path.name}")
    return data


def build(staging: Path, output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    staging = staging.resolve(strict=True)
    payload = {
        destination: (validate_arm64_elf(staging / source), 0o755)
        for destination, source in FILES.items()
    }
    payload["usr/local/share/t630/gtk-immodules.cache"] = (b"", 0o644)
    payload["usr/share/doc/t630-native-userspace/copyright"] = (
        (ROOT / "LICENSE").read_bytes(), 0o644)
    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: arm64
Maintainer: SM-T630 Ubuntu Port contributors
Depends: libc6, libdrm2, libgtk-3-0t64, libwayland-client0, libweston-13-0, libxcb1
Section: admin
Priority: optional
Description: native Ubuntu compatibility helpers for Samsung SM-T630
 Contains only redistributable ARM64 binaries built from repository source.
 Proprietary Samsung firmware and Android libraries are not included.
""".encode()
    control_archive = tar_bytes(
        {"control": (control, 0o644), "md5sums": (md5sums, 0o644),
         "postinst": (POSTINST, 0o755)}, epoch)
    data_archive = tar_bytes(payload, epoch)
    package = b"!<arch>\n"
    package += ar_member("debian-binary", b"2.0\n", epoch)
    package += ar_member("control.tar.xz", control_archive, epoch)
    package += ar_member("data.tar.xz", data_archive, epoch)
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
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_arm64.deb",
    )
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")),
    )
    args = parser.parse_args()
    digest = build(args.staging, args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
