#!/usr/bin/env python3
"""Build the account-neutral, source-only SM-T630 desktop runtime package."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-desktop-runtime"
VERSION = "0.1.4"

POSTINST = b"""#!/bin/sh
set -e
install -d -m 0700 /var/lib/t630
if ! getent group t630-owner >/dev/null; then
    addgroup --system t630-owner
fi
"""

FILES = {
    "usr/local/libexec/t630-app-grid": ("ubuntu/t630-app-grid.py", 0o755),
    "etc/polkit-1/rules.d/49-t630-sensorproxy.rules": ("ubuntu/49-t630-sensorproxy.rules", 0o644),
    "etc/udev/rules.d/71-t630-active-key.rules": ("ubuntu/71-t630-active-key.rules", 0o644),
    "etc/udev/rules.d/99-t630-input.rules": ("ubuntu/99-t630-input.rules", 0o644),
    "usr/local/bin/t630-app": ("ubuntu/t630-app", 0o755),
    "usr/local/bin/t630-display": ("ubuntu/t630-display-client.py", 0o755),
    "usr/local/bin/t630-gnome-preview": ("ubuntu/t630-gnome-preview", 0o755),
    "usr/local/bin/t630-gnome-run": ("ubuntu/t630-gnome-run.py", 0o755),
    "usr/local/bin/t630-gpu-env": ("ubuntu/t630-gpu-env", 0o755),
    "usr/local/lib/t630/t630_display.py": ("ubuntu/t630_display.py", 0o644),
    "usr/local/libexec/t630-auth-watch": ("ubuntu/t630-auth-watch.py", 0o755),
    "usr/local/libexec/t630-first-boot-resize": ("ubuntu/t630-first-boot-resize.py", 0o755),
    "usr/local/libexec/t630-first-boot-rotation": ("ubuntu/t630-first-boot-rotation.py", 0o755),
    "usr/local/libexec/t630-first-boot-session": ("ubuntu/t630-first-boot-session", 0o755),
    "usr/local/libexec/t630-controls": ("ubuntu/t630_controls.py", 0o755),
    "usr/local/libexec/t630-elogind-run": ("ubuntu/t630-elogind-run", 0o755),
    "usr/local/libexec/t630-gnome-session": ("ubuntu/t630-gnome-session", 0o755),
    "usr/local/libexec/t630-gnome-size.py": ("ubuntu/t630-gnome-size.py", 0o755),
    "usr/local/libexec/t630-gpu-session-watch": ("ubuntu/t630-gpu-session-watch.py", 0o755),
    "usr/local/libexec/t630-install-owner-assets": ("ubuntu/t630-install-owner-assets.py", 0o755),
    "usr/local/libexec/t630-lock-on-start": ("ubuntu/t630-lock-on-start.py", 0o755),
    "usr/local/libexec/t630-managed-session": ("ubuntu/t630-managed-session.py", 0o755),
    "usr/local/libexec/t630-password": ("ubuntu/t630_password.py", 0o755),
    "usr/local/libexec/t630-rotation-controller": ("ubuntu/t630-rotation-controller.py", 0o755),
    "usr/local/libexec/t630-session-manager": ("ubuntu/t630-session-manager.py", 0o755),
    "usr/local/libexec/t630-user-app": ("ubuntu/t630-user-app", 0o755),
    "usr/local/libexec/t630-x11-recovery": ("ubuntu/t630-x11-recovery.py", 0o755),
    "usr/local/sbin/t630-desktop-autostart": ("ubuntu/t630-desktop-autostart", 0o755),
    "usr/local/sbin/t630-login-start": ("ubuntu/t630-login-start", 0o755),
    "usr/local/sbin/t630-power-button": ("ubuntu/t630-power-button.py", 0o755),
    "usr/local/sbin/t630-pen-touch-guard": ("ubuntu/t630-pen-touch-guard.py", 0o755),
    "usr/local/sbin/t630-red-button": ("ubuntu/t630-red-button.py", 0o755),
    "usr/local/sbin/t630-suspend": ("ubuntu/t630-suspend.py", 0o755),
    "usr/local/share/t630/gnome-tablet-tools/extension.js": (
        "ubuntu/gnome-tablet-tools/extension.js", 0o644),
    "usr/local/share/t630/gnome-tablet-tools/metadata.json": (
        "ubuntu/gnome-tablet-tools/metadata.json", 0o644),
    "usr/local/share/t630/gnome-tablet-tools/schemas/org.gnome.shell.extensions.t630-tablet-tools.gschema.xml": (
        "ubuntu/gnome-tablet-tools/schemas/org.gnome.shell.extensions.t630-tablet-tools.gschema.xml",
        0o644,
    ),
    "usr/share/doc/t630-desktop-runtime/copyright": ("LICENSE", 0o644),
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
Depends: t630-first-boot (= 0.1.1), t630-native-userspace (= 0.1.0), python3, python3-gi, gnome-shell, gnome-control-center, at-spi2-core, xdg-user-dirs, xwayland, xauth, x11-utils, xdotool, libglib2.0-bin, util-linux
Section: admin
Priority: optional
Description: account-neutral Ubuntu desktop integration for Samsung SM-T630
 Installs the tracked desktop, input, rotation, login, display-power and shallow
 suspend glue. Matching native helper binaries and stock-derived firmware are
 deliberately packaged separately.
""".encode()
    control_archive = tar_bytes({
        "control": (control, 0o644),
        "md5sums": (md5sums, 0o644),
        "postinst": (POSTINST, 0o755),
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
