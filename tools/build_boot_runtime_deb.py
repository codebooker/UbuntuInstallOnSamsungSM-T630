#!/usr/bin/env python3
"""Build the reproducible host-compositor runtime for the SM-T630."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-boot-runtime"
VERSION = "0.1.1"
WESTON_KEYBOARD = "/usr/libexec/weston-keyboard"
MALIIT_QML = "/usr/lib/aarch64-linux-gnu/maliit/keyboard2/qml/Keyboard.qml"
FILES = {
    "etc/chrony/t630.conf": ("ubuntu/chrony-ram.conf", 0o644),
    "etc/t630/keyboard-mode": ("ubuntu/keyboard-mode", 0o644),
    "usr/libexec/weston-keyboard": ("ubuntu/t630-keyboard", 0o755),
    "usr/lib/aarch64-linux-gnu/maliit/keyboard2/qml/Keyboard.qml": (
        "ubuntu/MaliitKeyboard.qml", 0o644),
    "usr/local/libexec/t630-install-gnome-guards": (
        "ubuntu/install-t630-keyboard-guard.py", 0o755),
    "usr/local/libexec/t630-install-keyboard-icons": (
        "ubuntu/install-keyboard-icons.sh", 0o755),
    "usr/local/libexec/t630-render-launcher-icons": (
        "ubuntu/render_launcher_icons.py", 0o755),
    "usr/local/share/t630/weston.ini": ("ubuntu/weston-desktop.ini", 0o644),
    "usr/share/doc/t630-boot-runtime/copyright": ("LICENSE", 0o644),
}

PREINST = f"""#!/bin/sh
set -e
for path in {WESTON_KEYBOARD} {MALIIT_QML}; do
    dpkg-divert --package {PACKAGE} --add --rename \\
        --divert "$path.t630-stock" "$path"
done
""".encode()

POSTINST = b"""#!/bin/sh
set -e
/usr/local/libexec/t630-install-keyboard-icons
/usr/bin/python3 /usr/local/libexec/t630-render-launcher-icons
/usr/bin/python3 /usr/local/libexec/t630-install-gnome-guards
"""

POSTRM = f"""#!/bin/sh
set -e
if [ "$1" = remove ] || [ "$1" = purge ]; then
    for path in {MALIIT_QML} {WESTON_KEYBOARD}; do
        dpkg-divert --package {PACKAGE} --remove --rename \\
            --divert "$path.t630-stock" "$path"
    done
    rm -f \
        /usr/local/share/t630/icons/controls.png \
        /usr/local/share/t630/icons/files.png \
        /usr/local/share/t630/icons/editor.png \
        /usr/local/share/t630/gnome-resource-overlay/keyboard.js \
        /usr/local/share/t630/gnome-resource-overlay/unlockDialog.js \
        /usr/local/share/icons/hicolor/scalable/actions/keyboard-caps-disabled-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/keyboard-caps-enabled-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/keyboard-caps-locked-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/keyboard-enter-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/keyboard-spacebar-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/edit-clear-symbolic.svg \
        /usr/local/share/icons/hicolor/scalable/actions/edit-clear-symoblic.svg \
        /usr/local/share/icons/hicolor/icon-theme.cache \
        /usr/local/share/icons/hicolor/index.theme
    rmdir --ignore-fail-on-non-empty \
        /usr/local/share/t630/icons \
        /usr/local/share/t630/gnome-resource-overlay \
        /usr/local/share/t630 \
        /usr/local/share/icons/hicolor/scalable/actions \
        /usr/local/share/icons/hicolor/scalable \
        /usr/local/share/icons/hicolor 2>/dev/null || true
fi
""".encode()


def build(output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    payload = {}
    for destination, (source, mode) in FILES.items():
        path = ROOT / source
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
        payload[destination] = (path.read_bytes(), mode)
    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: all
Maintainer: SM-T630 Ubuntu Port contributors
Depends: t630-hardware-runtime (>= 0.1.6), weston (= 13.0.0-4build3), seatd, chrony, maliit-keyboard (= 2.3.1-5build2), maliit-framework (= 2.3.0-4build5), qtwayland5, breeze-icon-theme, libqt5svg5, librsvg2-common, gnome-shell (= 46.0-0ubuntu6~24.04.14), python3-gi, gir1.2-gtk-3.0, libglib2.0-bin
Section: admin
Priority: optional
Description: host compositor and keyboard runtime for Samsung SM-T630
 Installs the pinned Weston/Maliit integration, clock policy, launcher assets,
 and version-checked GNOME lock-screen guards used before and after first boot.
""".encode()
    control_archive = tar_bytes({
        "control": (control, 0o644),
        "md5sums": (md5sums, 0o644),
        "preinst": (PREINST, 0o755),
        "postinst": (POSTINST, 0o755),
        "postrm": (POSTRM, 0o755),
    }, epoch)
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
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "output" / f"{PACKAGE}_{VERSION}_all.deb")
    parser.add_argument(
        "--source-date-epoch", type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")))
    args = parser.parse_args()
    digest = build(args.output.resolve(), args.source_date_epoch)
    print(f"{args.output}: SHA256 {digest}")


if __name__ == "__main__":
    main()
