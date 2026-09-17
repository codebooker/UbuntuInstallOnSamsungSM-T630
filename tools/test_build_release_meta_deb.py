#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_release_meta_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_release_meta_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


class ReleaseMetaPackageTests(unittest.TestCase):
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

    def test_reproducible_exact_dependency_set(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.deb", root / "two.deb"
            self.assertEqual(builder.build(one, 1700000000),
                             builder.build(two, 1700000000))
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = self.ar_members(one.read_bytes())
            control_path = root / "control.tar.xz"
            control_path.write_bytes(members["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as archive:
                control = archive.extractfile("./control").read().decode()
            for dependency in builder.DEPENDENCIES:
                self.assertIn(dependency, control)
            self.assertIn("Architecture: arm64", control)

    def test_every_device_package_is_version_locked(self):
        self.assertGreaterEqual(len(builder.DEPENDENCIES), 11)
        self.assertTrue(all(" (= " in item for item in builder.DEPENDENCIES))
        self.assertTrue(any(item.startswith("t630-stock-assets")
                            for item in builder.DEPENDENCIES))
        self.assertTrue(any(item.startswith("t630-pd-mapper")
                            for item in builder.DEPENDENCIES))
        self.assertIn("t630-boot-runtime (= 0.1.1)", builder.DEPENDENCIES)
        self.assertIn("t630-polkit-runtime (= 0.1.0)", builder.DEPENDENCIES)
        self.assertIn("t630-login-runtime (= 0.1.2)", builder.DEPENDENCIES)
        self.assertIn("t630-first-boot (= 0.1.2)", builder.DEPENDENCIES)
        self.assertIn("t630-desktop-runtime (= 0.1.10)", builder.DEPENDENCIES)
        self.assertIn("t630-camera-runtime (= 0.1.6)", builder.DEPENDENCIES)


if __name__ == "__main__":
    unittest.main()
