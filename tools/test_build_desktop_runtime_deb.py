#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_desktop_runtime_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_desktop_runtime_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)

class DesktopRuntimePackageTests(unittest.TestCase):
    def ar_members(self, package: bytes):
        self.assertTrue(package.startswith(b"!<arch>\n"))
        offset = 8
        result = {}
        while offset < len(package):
            header = package[offset:offset + 60]
            self.assertEqual(header[58:60], b"`\n")
            name = header[:16].decode().strip().rstrip("/")
            size = int(header[48:58].decode().strip())
            start = offset + 60
            result[name] = package[start:start + size]
            offset = start + size + (size % 2)
        return result

    def test_build_is_reproducible_and_account_neutral(self):
        with tempfile.TemporaryDirectory() as directory:
            one = Path(directory) / "one.deb"
            two = Path(directory) / "two.deb"
            self.assertEqual(builder.build(one, 1700000000), builder.build(two, 1700000000))
            self.assertEqual(one.read_bytes(), two.read_bytes())
            archive = self.ar_members(one.read_bytes())
            control_path = Path(directory) / "control.tar.xz"
            control_path.write_bytes(archive["control.tar.xz"])
            with tarfile.open(control_path, "r:xz") as control_archive:
                control = control_archive.extractfile("./control").read().decode()
                postinst = control_archive.extractfile("./postinst").read().decode()
            self.assertIn("Package: t630-desktop-runtime\n", control)
            self.assertIn("t630-first-boot (= 0.1.1)", control)
            self.assertIn("t630-native-userspace (= 0.1.0)", control)
            self.assertIn("addgroup --system t630-owner", postinst)
            session = (builder.ROOT / "ubuntu/t630-first-boot-session").read_text()
            ready = session.index('until [ -S "$runtime/$wayland_name" ]')
            keyboard = session.rindex(
                "gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true")
            self.assertLess(ready, keyboard)
            self.assertIn("GTK_THEME=Adwaita:dark", session)
            self.assertIn("-extension GLX", session)
            owner_session = (builder.ROOT / "ubuntu/t630-gnome-session").read_text()
            self.assertIn("-extension MIT-SHM -extension GLX", owner_session)
            data_path = Path(directory) / "data.tar.xz"
            data_path.write_bytes(archive["data.tar.xz"])
            with tarfile.open(data_path, "r:xz") as payload:
                names = {entry.name.removeprefix("./") for entry in payload.getmembers()}
            self.assertIn("usr/local/libexec/t630-x11-recovery", names)
            self.assertIn("usr/local/libexec/t630-install-owner-assets", names)
            self.assertIn("usr/local/share/t630/gnome-tablet-tools/extension.js", names)
            self.assertIn("usr/local/sbin/t630-suspend", names)
            self.assertIn("usr/local/libexec/t630-first-boot-session", names)
            self.assertIn("usr/local/libexec/t630-first-boot-resize", names)
            self.assertIn("usr/local/libexec/t630-first-boot-rotation", names)
            self.assertFalse(any(name.startswith("home/") for name in names))
            self.assertFalse(any("first-boot-profile.json" in name for name in names))

    def test_every_payload_source_is_tracked_and_not_a_symlink(self):
        for source, _mode in builder.FILES.values():
            with self.subTest(source=source):
                path = builder.ROOT / source
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())


if __name__ == "__main__":
    unittest.main()
