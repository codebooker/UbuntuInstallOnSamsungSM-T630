#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_camera_runtime_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_camera_runtime_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def fake_arm64_elf() -> bytes:
    data = bytearray(64)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", data, 16, 3, 183)
    return bytes(data)


class CameraRuntimePackageTests(unittest.TestCase):
    @staticmethod
    def ar_members(package: bytes) -> dict[str, bytes]:
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

    def test_reproducible_and_contains_no_private_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            staging.mkdir()
            for name in builder.NATIVE_FILES.values():
                (staging / name).write_bytes(fake_arm64_elf())
            one, two = root / "one.deb", root / "two.deb"
            self.assertEqual(
                builder.build(staging, one, 1700000000),
                builder.build(staging, two, 1700000000),
            )
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = self.ar_members(one.read_bytes())
            archive_path = root / "data.tar.xz"
            archive_path.write_bytes(members["data.tar.xz"])
            with tarfile.open(archive_path, "r:xz") as archive:
                names = {item.name.removeprefix("./") for item in archive.getmembers()}
            self.assertIn("usr/local/libexec/t630-camera-capture", names)
            self.assertIn("usr/local/libexec/t630-binder-placeholder", names)
            self.assertIn("usr/local/sbin/t630-camera-control", names)
            self.assertIn("usr/share/applications/t630-camera.desktop", names)
            self.assertFalse(any(name.startswith(("home/", "data/", "vendor/"))
                                 for name in names))
            self.assertFalse(any(name.endswith((".img", ".bin", ".mbn", ".elf"))
                                 for name in names))

    def test_control_keeps_stock_asset_boundary_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            staging.mkdir()
            for name in builder.NATIVE_FILES.values():
                (staging / name).write_bytes(fake_arm64_elf())
            package = root / "camera.deb"
            builder.build(staging, package, 1700000000)
            members = self.ar_members(package.read_bytes())
            control_path = root / "control.tar.xz"
            control_path.write_bytes(members["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as archive:
                control = archive.extractfile("./control").read().decode()
            self.assertIn("Version: 0.1.3", control)
            self.assertIn("t630-stock-assets (= 1.0.1+dze3)", control)
            self.assertIn("must be reconstructed locally", control)

    def test_runtime_uses_packaged_helper_paths(self):
        mounts = (builder.ROOT / "camera/t630-camera-mounts.sh").read_text()
        stack = (builder.ROOT / "camera/t630-camera-stack.sh").read_text()
        bridge = (builder.ROOT / "ubuntu/t630-camera-bridge").read_text()
        self.assertIn("/usr/local/libexec/t630-binder-placeholder", stack)
        self.assertIn("/usr/local/libexec/t630-camera-capture", bridge)
        self.assertNotIn("/data/vendor/camera/t630-binder-placeholder", stack)
        self.assertNotIn("/data/vendor/camera/t630-camera-capture", bridge)
        self.assertIn("/var/lib/t630-camera/android-data", mounts)
        self.assertNotIn('"$T630_OWNER_HOME/t630-android-data"', mounts)
        self.assertIn("/var/lib/t630-camera/static", mounts)
        self.assertNotIn("T630_OWNER_HOME", mounts)


if __name__ == "__main__":
    unittest.main()
