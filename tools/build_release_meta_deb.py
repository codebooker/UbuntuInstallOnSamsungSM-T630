#!/usr/bin/env python3
"""Build the exact-version SM-T630 base release package set."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-release-base"
VERSION = "0.1.23"
DEPENDENCIES = (
    "t630-first-boot (= 0.1.3)",
    "t630-desktop-runtime (= 0.1.14)",
    "t630-hardware-runtime (= 0.1.6)",
    "t630-boot-runtime (= 0.1.1)",
    "t630-polkit-runtime (= 0.1.0)",
    "t630-login-runtime (= 0.1.2)",
    "t630-camera-runtime (= 0.1.7)",
    "t630-native-userspace (= 0.1.0)",
    "t630-pd-mapper (= 0.1.0)",
    "libssc (= 0.4.4-t6303)",
    "hexagonrpcd (= 0.4.0-t6303)",
    "iio-sensor-proxy (= 3.9-t6303)",
    "t630-stock-assets (= 1.0.2+dze3)",
)


def build(output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    package_set = (json.dumps({
        "device": "Samsung SM-T630",
        "stock_baseline": "T630XXSBDZE3",
        "packages": list(DEPENDENCIES),
    }, indent=2, sort_keys=True) + "\n").encode()
    payload = {
        "usr/share/doc/t630-release-base/package-set.json": (package_set, 0o644),
        "usr/share/doc/t630-release-base/copyright": (
            (ROOT / "LICENSE").read_bytes(), 0o644),
    }
    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: arm64
Maintainer: SM-T630 Ubuntu Port contributors
Depends: {', '.join(DEPENDENCIES)}
Section: metapackages
Priority: optional
Description: exact native Ubuntu base package set for Samsung SM-T630
 Pulls together the reproducible device integration, redistributable camera
 compatibility runtime and the owner's private exact-DZE3 stock-assets package.
 The larger proprietary camera runtime must still be reconstructed locally.
""".encode()
    package = b"!<arch>\n"
    package += ar_member("debian-binary", b"2.0\n", epoch)
    package += ar_member("control.tar.xz", tar_bytes({
        "control": (control, 0o644), "md5sums": (md5sums, 0o644)}, epoch), epoch)
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
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_arm64.deb")
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")))
    args = parser.parse_args()
    digest = build(args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
