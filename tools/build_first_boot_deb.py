#!/usr/bin/env python3
"""Build the redistributable, account-neutral SM-T630 first-boot package."""

from __future__ import annotations

import argparse
import hashlib
import io
import lzma
import os
from pathlib import Path
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "t630-first-boot"
VERSION = "0.1.1"

FILES = {
    "usr/local/libexec/t630-first-boot": ("ubuntu/t630-first-boot-ui.py", 0o755),
    "usr/local/bin/t630-connect-wifi": ("ubuntu/connect_wifi.py", 0o755),
    "usr/local/share/t630/t630_account.py": ("ubuntu/t630_account.py", 0o755),
    "usr/local/share/t630/t630_first_boot.py": ("ubuntu/t630_first_boot.py", 0o755),
    "usr/local/share/t630/t630-apply-user-profile.py": (
        "ubuntu/t630-apply-user-profile.py",
        0o755,
    ),
    "usr/share/doc/t630-first-boot/examples/first-boot-profile.json": (
        "docs/examples/first-boot-profile.json",
        0o644,
    ),
    "usr/share/doc/t630-first-boot/copyright": ("LICENSE", 0o644),
}


def tar_bytes(files: dict[str, tuple[bytes, int]], epoch: int) -> bytes:
    """Return a deterministic xz-compressed ustar archive."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        directories = set()
        for name in files:
            path = Path(name)
            for parent in path.parents:
                if str(parent) != ".":
                    directories.add(str(parent))
        for directory in sorted(directories):
            info = tarfile.TarInfo(f"./{directory}/")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = epoch
            archive.addfile(info)
        for name, (data, mode) in sorted(files.items()):
            info = tarfile.TarInfo(f"./{name}")
            info.size = len(data)
            info.mode = mode
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = epoch
            archive.addfile(info, io.BytesIO(data))
    return lzma.compress(raw.getvalue(), format=lzma.FORMAT_XZ, preset=9)


def ar_member(name: str, data: bytes, epoch: int) -> bytes:
    """Encode one portable System V ar member used by the deb format."""
    encoded_name = f"{name}/"
    if len(encoded_name) > 16:
        raise ValueError(f"ar member name is too long: {name}")
    header = (
        f"{encoded_name:<16}{epoch:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n"
    ).encode("ascii")
    return header + data + (b"\n" if len(data) % 2 else b"")


def build(output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")

    payload: dict[str, tuple[bytes, int]] = {}
    for destination, (source, mode) in FILES.items():
        source_path = ROOT / source
        if not source_path.is_file():
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
Depends: python3, python3-gi, gir1.2-gtk-3.0, locales, passwd, network-manager
Section: admin
Priority: optional
Description: touch-first account setup for Ubuntu on the Samsung SM-T630
 Creates the first human account and applies locale, keyboard, time-zone,
 accessibility, privacy, and network choices without embedding a development
 account or password in the release image.
""".encode()

    control_archive = tar_bytes(
        {
            "control": (control, 0o644),
            "md5sums": (md5sums, 0o644),
        },
        epoch,
    )
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
        "--output",
        type=Path,
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_all.deb",
    )
    parser.add_argument(
        "--source-date-epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")),
    )
    args = parser.parse_args()
    digest = build(args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
