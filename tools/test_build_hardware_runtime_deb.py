#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_hardware_runtime_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_hardware_runtime_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


class HardwareRuntimePackageTests(unittest.TestCase):
    def ar_members(self, package):
        offset = 8
        result = {}
        while offset < len(package):
            header = package[offset:offset + 60]
            name = header[:16].decode().strip().rstrip("/")
            size = int(header[48:58].decode().strip())
            start = offset + 60
            result[name] = package[start:start + size]
            offset = start + size + (size % 2)
        return result

    def test_reproducible_source_only_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.deb", root / "two.deb"
            self.assertEqual(builder.build(one, 1700000000), builder.build(two, 1700000000))
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = self.ar_members(one.read_bytes())
            data_path = root / "data.tar.xz"
            data_path.write_bytes(members["data.tar.xz"])
            with tarfile.open(data_path, "r:xz") as archive:
                names = {item.name.removeprefix("./") for item in archive.getmembers()}
            self.assertIn("usr/local/sbin/t630-audio-start", names)
            self.assertIn("etc/t630-install-id", names)
            self.assertIn("usr/local/libexec/t630-bluetooth/t630_qca_bt.py", names)
            self.assertIn("usr/local/sbin/t630-sensors-start", names)
            self.assertIn("usr/local/share/t630/mdev.conf", names)
            self.assertIn("usr/local/share/t630/test-speaker-protection.py", names)
            self.assertIn(
                "usr/local/share/t630/owner-config/wireplumber/main.lua.d/51-t630-manual-alsa.lua",
                names,
            )
            self.assertFalse(any(name.startswith("home/") for name in names))
            self.assertFalse(any(name.startswith("opt/t630/") for name in names))
            self.assertFalse(any(name.endswith((".so", ".bin", ".tlv", ".mdt")) for name in names))
            sensors = (builder.ROOT / "ubuntu/t630-sensors-start").read_text()
            self.assertIn('T630_FIRST_BOOT:-0', sensors)

    def test_control_declares_unfinished_local_asset_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "package.deb"
            builder.build(package, 1700000000)
            members = self.ar_members(package.read_bytes())
            control_path = Path(directory) / "control.tar.xz"
            control_path.write_bytes(members["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as archive:
                control = archive.extractfile("./control").read().decode()
            self.assertIn("t630-desktop-runtime (= 0.1.4)", control)
            self.assertIn("wpasupplicant", control)
            self.assertIn("pulseaudio-utils", control)
            self.assertIn("libssc (>= 0.4.4-t6303)", control)
            self.assertIn("hexagonrpcd (>= 0.4.0-t6303)", control)
            self.assertIn("iio-sensor-proxy (>= 3.9-t6303)", control)
            self.assertIn("t630-stock-assets", control)


if __name__ == "__main__":
    unittest.main()
