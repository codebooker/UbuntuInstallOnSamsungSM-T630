#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_boot_runtime_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_boot_runtime_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def ar_members(package: bytes):
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


class BootRuntimePackageTests(unittest.TestCase):
    def test_reproducible_package_has_diversions_and_boot_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one, two = root / "one.deb", root / "two.deb"
            self.assertEqual(builder.build(one, 1700000000),
                             builder.build(two, 1700000000))
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = ar_members(one.read_bytes())
            control_path = root / "control.tar.xz"
            control_path.write_bytes(members["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as archive:
                control = archive.extractfile("./control").read().decode()
                preinst = archive.extractfile("./preinst").read().decode()
                postinst = archive.extractfile("./postinst").read().decode()
                postrm = archive.extractfile("./postrm").read().decode()
            self.assertIn("weston (= 13.0.0-4build3)", control)
            self.assertIn("maliit-keyboard (= 2.3.1-5build2)", control)
            self.assertIn("librsvg2-common", control)
            self.assertIn("dpkg-divert", preinst)
            self.assertIn("--add --rename", preinst)
            self.assertIn("t630-install-gnome-guards", postinst)
            self.assertIn("--remove --rename", postrm)
            self.assertIn("gnome-resource-overlay/keyboard.js", postrm)
            self.assertIn("keyboard-enter-symbolic.svg", postrm)

            data_path = root / "data.tar.xz"
            data_path.write_bytes(members["data.tar.xz"])
            with tarfile.open(data_path, "r:xz") as archive:
                names = {item.name.removeprefix("./") for item in archive}
            self.assertIn("usr/local/share/t630/weston.ini", names)
            self.assertIn("usr/libexec/weston-keyboard", names)
            self.assertIn(builder.MALIIT_QML.removeprefix("/"), names)
            self.assertEqual(
                builder.MALIIT_QML,
                "/usr/lib/aarch64-linux-gnu/maliit/keyboard2/qml/Keyboard.qml",
            )
            self.assertIn("etc/chrony/t630.conf", names)

    def test_payload_sources_are_regular_files(self):
        for source, _mode in builder.FILES.values():
            with self.subTest(source=source):
                path = builder.ROOT / source
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())


if __name__ == "__main__":
    unittest.main()
