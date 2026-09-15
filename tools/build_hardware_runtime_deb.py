#!/usr/bin/env python3
"""Build the redistributable, source-only SM-T630 hardware orchestration package."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile

from build_first_boot_deb import ROOT, ar_member, tar_bytes


PACKAGE = "t630-hardware-runtime"
VERSION = "0.1.2"
FILES = {
    "etc/t630-install-id": ("ubuntu/t630-install-id", 0o644),
    "etc/NetworkManager/conf.d/90-t630-network.conf": ("ubuntu/90-t630-network.conf", 0o644),
    "etc/udev/rules.d/61-t630-sensors.rules": ("ubuntu/61-t630-sensors.rules", 0o644),
    "usr/local/bin/t630-microphone-bridge": ("ubuntu/t630-microphone-bridge", 0o755),
    "usr/local/libexec/t630-bluetooth/t630_qca_bt.py": ("tools/t630_qca_bt.py", 0o755),
    "usr/local/sbin/t630-audio-start": ("ubuntu/t630-audio-start", 0o755),
    "usr/local/sbin/t630-bluetooth-start": ("ubuntu/t630-bluetooth-start", 0o755),
    "usr/local/sbin/t630-bluetooth-supervisor": ("ubuntu/t630-bluetooth-supervisor", 0o755),
    "usr/local/sbin/t630-ipa-start": ("ubuntu/t630-ipa-start.py", 0o755),
    "usr/local/sbin/t630-sensors-start": ("ubuntu/t630-sensors-start", 0o755),
    "usr/local/share/t630/apply-stock-speaker-preset.py": (
        "ubuntu/apply-stock-speaker-preset.py", 0o755),
    "usr/local/share/t630/load-stock-speaker-calibration.py": (
        "ubuntu/load-stock-speaker-calibration.py", 0o755),
    "usr/local/share/t630/reapply-speaker-calibration.py": (
        "ubuntu/reapply-speaker-calibration.py", 0o755),
    "usr/local/share/t630/stage-audio-firmware.sh": ("ubuntu/stage-audio-firmware.sh", 0o755),
    "usr/local/share/t630/stage-video-firmware.sh": ("ubuntu/stage-video-firmware.sh", 0o755),
    "usr/local/share/t630/t630-audio-modules.py": ("ubuntu/t630-audio-modules.py", 0o755),
    "usr/local/share/t630/t630-audio-session-cleanup.py": (
        "ubuntu/t630-audio-session-cleanup.py", 0o755),
    "usr/local/share/t630/t630-device-permissions.py": (
        "ubuntu/t630-device-permissions.py", 0o755),
    "usr/local/share/t630/t630-microphone-route.py": (
        "ubuntu/t630-microphone-route.py", 0o755),
    "usr/local/share/t630/t630-sound-nodes.py": ("ubuntu/t630-sound-nodes.py", 0o755),
    "usr/local/share/t630/t630-speaker-route.py": ("ubuntu/t630-speaker-route.py", 0o755),
    "usr/local/share/t630/test-audio-cold-order.sh": ("ubuntu/test-audio-cold-order.sh", 0o755),
    "usr/local/share/t630/owner-config/wireplumber/bluetooth.lua.d/51-t630-bluetooth.lua": (
        "ubuntu/51-t630-bluetooth.lua", 0o644),
    "usr/local/share/t630/owner-config/wireplumber/main.lua.d/51-t630-manual-alsa.lua": (
        "ubuntu/51-t630-manual-alsa.lua", 0o644),
    "usr/share/doc/t630-hardware-runtime/copyright": ("LICENSE", 0o644),
}


def build(output: Path, epoch: int) -> str:
    if epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")
    payload = {}
    for destination, (source, mode) in FILES.items():
        source_path = ROOT / source
        if not source_path.is_file() or source_path.is_symlink():
            raise FileNotFoundError(source_path)
        data = source_path.read_bytes()
        if source != "LICENSE":
            data.decode("utf-8")
        payload[destination] = (data, mode)
    md5sums = "".join(
        f"{hashlib.md5(data, usedforsecurity=False).hexdigest()}  {name}\n"
        for name, (data, _mode) in sorted(payload.items())
    ).encode()
    control = f"""Package: {PACKAGE}
Version: {VERSION}
Architecture: all
Maintainer: SM-T630 Ubuntu Port contributors
Depends: t630-desktop-runtime (= 0.1.1), python3, network-manager, wpasupplicant, bluez, pipewire, pipewire-pulse, wireplumber, alsa-utils, iio-sensor-proxy, util-linux
Recommends: libssc (>= 0.4.4-t6303), hexagonrpcd (>= 0.4.0-t6303), iio-sensor-proxy (>= 3.9-t6303), t630-stock-assets
Section: admin
Priority: optional
Description: hardware service orchestration for Ubuntu on Samsung SM-T630
 Contains only redistributable scripts and policy. Proprietary firmware,
 calibration, Android libraries, compiled daemons and device identity are absent.
""".encode()
    control_archive = tar_bytes(
        {"control": (control, 0o644), "md5sums": (md5sums, 0o644)}, epoch)
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
