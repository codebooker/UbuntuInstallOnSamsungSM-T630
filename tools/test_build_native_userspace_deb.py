#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_native_userspace_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_native_userspace_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def fake_elf(machine=183):
    value = bytearray(64)
    value[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", value, 16, 3, machine)
    return bytes(value)


class NativeUserspacePackageTests(unittest.TestCase):
    def staging(self, root):
        stage = root / "stage"
        stage.mkdir()
        for name in builder.FILES.values():
            (stage / name).write_bytes(fake_elf())
        return stage

    def ar_members(self, package):
        self.assertTrue(package.startswith(b"!<arch>\n"))
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

    def test_reproducible_arm64_package_and_postinst(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = self.staging(root)
            one, two = root / "one.deb", root / "two.deb"
            self.assertEqual(builder.build(stage, one, 1700000000),
                             builder.build(stage, two, 1700000000))
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = self.ar_members(one.read_bytes())
            control_path = root / "control.tar.xz"
            control_path.write_bytes(members["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as archive:
                control = archive.extractfile("./control").read().decode()
                postinst = archive.extractfile("./postinst").read().decode()
            self.assertIn("Architecture: arm64", control)
            self.assertIn("gtk-query-immodules-3.0", postinst)

    def test_rejects_wrong_architecture_and_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrong = root / "wrong"
            wrong.write_bytes(fake_elf(machine=62))
            with self.assertRaises(ValueError):
                builder.validate_arm64_elf(wrong)
            target = root / "target"
            target.write_bytes(fake_elf())
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                builder.validate_arm64_elf(link)


if __name__ == "__main__":
    unittest.main()
