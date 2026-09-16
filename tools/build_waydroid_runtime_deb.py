#!/usr/bin/env python3
"""Build the SM-T630 Waydroid integration package reproducibly."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-waydroid-runtime"
VERSION = "0.1.5"

FILES = {
    "usr/local/bin/lxc-start": ("ubuntu/t630-waydroid-lxc-start", 0o755),
    "usr/local/bin/waydroid": ("ubuntu/t630-waydroid", 0o755),
    "usr/local/sbin/t630-waydroid-prepare": (
        "ubuntu/t630-waydroid-prepare", 0o755),
    "usr/local/sbin/t630-check-waydroid-gapps": (
        "tools/check_waydroid_gapps.py", 0o755),
    "usr/share/doc/t630-waydroid-runtime/copyright": ("LICENSE", 0o644),
}


def build(output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    payload = {}
    for destination, (source, mode) in FILES.items():
        source_path = ROOT / source
        if not source_path.is_file() or source_path.is_symlink():
            raise FileNotFoundError(source_path)
        payload[destination] = (source_path.read_bytes(), mode)
    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: all
Maintainer: SM-T630 Ubuntu Port contributors
Depends: waydroid (= 1.6.2), lxc (= 1:5.0.3-2ubuntu7.2), python3, util-linux
Section: admin
Priority: optional
Description: Waydroid integration for the Samsung SM-T630 Ubuntu port
 Adds deterministic cgroup-v1 and binderfs preparation, the outer-root LXC
 launcher required by the recovery-hosted Ubuntu filesystem, and the nested
 GNOME compositor environment used by Android application launchers. Includes
 a read-only GAPPS acceptance checker that suppresses account identifiers.
""".encode()
    control_archive = tar_bytes({
        "control": (control, 0o644),
        "md5sums": (md5sums, 0o644),
    }, epoch)
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
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_all.deb",
    )
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")),
    )
    args = parser.parse_args()
    digest = build(args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
