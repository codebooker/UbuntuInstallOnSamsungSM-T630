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
    def test_touchscreen_and_pen_share_libinput_group(self):
        rules = (builder.ROOT / "ubuntu/99-t630-input.rules").read_text()
        group = 'ENV{LIBINPUT_DEVICE_GROUP}="t630-integrated-pen-touch"'
        self.assertEqual(rules.count(group), 2)
        self.assertIn('ATTRS{name}=="sec_e-pen"', rules)
        self.assertIn('ATTRS{name}=="sec_touchscreen"', rules)

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
            self.assertIn("Version: 0.1.14", control)
            self.assertIn("t630-first-boot (= 0.1.3)", control)
            self.assertIn("t630-native-userspace (= 0.1.0)", control)
            self.assertIn("gnome-control-center", control)
            self.assertIn("sudo", control)
            self.assertIn("gdisk", control)
            self.assertIn("at-spi2-core", control)
            self.assertIn("xdg-user-dirs", control)
            self.assertIn("addgroup --system t630-owner", postinst)
            session = (builder.ROOT / "ubuntu/t630-first-boot-session").read_text()
            ready = session.index('until [ -S "$runtime/$wayland_name" ]')
            keyboard = session.rindex(
                "gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true")
            self.assertLess(ready, keyboard)
            self.assertIn("GTK_THEME=Adwaita:dark", session)
            self.assertLess(session.index("test-audio-cold-order.sh"),
                            session.index("t630-sensors-start"))
            self.assertIn("-extension GLX", session)
            self.assertIn("--nested --wayland --no-x11", session)
            owner_session = (builder.ROOT / "ubuntu/t630-gnome-session").read_text()
            self.assertIn("-extension MIT-SHM -extension GLX", owner_session)
            self.assertIn("--nested --wayland --no-x11", owner_session)
            self.assertIn('/usr/bin/xdg-user-dirs-update', owner_session)
            self.assertIn("XF86HomePage", owner_session)
            self.assertIn("XF86Launch6", owner_session)
            self.assertIn(
                "org.gnome.desktop.wm.preferences button-layout ':minimize,maximize,close'",
                owner_session,
            )
            self.assertIn('/usr/local/libexec/t630-app-grid', owner_session)
            self.assertIn('/usr/local/libexec/t630-chrome-ime', owner_session)
            self.assertIn('/usr/local/libexec/t630-chrome-osk', owner_session)
            self.assertIn('toolkit-accessibility true', owner_session)
            self.assertLess(owner_session.index('/usr/local/libexec/t630-app-grid'),
                            owner_session.index('/usr/bin/gnome-shell --nested'))
            self.assertNotIn('gsettings set org.gnome.shell favorite-apps', owner_session)
            self.assertNotIn("org.gnome.desktop.background picture-options", owner_session)
            self.assertNotIn("org.gnome.desktop.background primary-color", owner_session)
            manager = (builder.ROOT / "ubuntu/t630-session-manager.py").read_text()
            for method in ("Logout", "Shutdown", "Reboot", "CanShutdown", "IsInhibited"):
                self.assertIn(f"name='{method}'", manager)
            self.assertIn("EndSessionDialog", manager)
            extension = (builder.ROOT / "ubuntu/gnome-tablet-tools/extension.js").read_text()
            self.assertIn("title: 'Settings'", extension)
            self.assertIn("/usr/local/bin/t630-gnome-run", extension)
            self.assertIn("/usr/bin/gnome-control-center", extension)
            self.assertNotIn("Waydroid", extension)
            self.assertIn("title: 'Restart into Android'", extension)
            self.assertIn("/usr/local/libexec/t630-switch-dialog", extension)
            self.assertIn('method name="ShowKeyboard"', extension)
            self.assertIn('method name="HideKeyboard"', extension)
            autostart = (builder.ROOT / "ubuntu/t630-desktop-autostart").read_text()
            self.assertIn('if [ -e /run/t630-recovery-terminal ]', autostart)
            self.assertNotIn('t630-waydroid-prepare', autostart)
            data_path = Path(directory) / "data.tar.xz"
            data_path.write_bytes(archive["data.tar.xz"])
            with tarfile.open(data_path, "r:xz") as payload:
                names = {entry.name.removeprefix("./") for entry in payload.getmembers()}
            self.assertIn("usr/local/libexec/t630-x11-recovery", names)
            self.assertIn("usr/local/libexec/t630-chrome-ime", names)
            self.assertIn("usr/local/libexec/t630-chrome-osk", names)
            self.assertIn("usr/local/libexec/t630-install-owner-assets", names)
            self.assertIn("usr/local/share/t630/gnome-tablet-tools/extension.js", names)
            self.assertIn("usr/local/sbin/t630-suspend", names)
            self.assertIn("usr/local/sbin/t630-switch-to-native-android", names)
            self.assertIn("usr/local/libexec/t630-switch-dialog", names)
            self.assertIn("etc/sudoers.d/t630-dualboot", names)
            self.assertIn("usr/local/libexec/t630-first-boot-session", names)
            self.assertIn("usr/local/libexec/t630-first-boot-resize", names)
            self.assertIn("usr/local/libexec/t630-first-boot-rotation", names)
            self.assertFalse(any(name.startswith("home/") for name in names))
            self.assertFalse(any("first-boot-profile.json" in name for name in names))
            switcher = (builder.ROOT / "tools/switch_to_native_android.sh").read_text()
            self.assertIn(
                "9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e",
                switcher,
            )

    def test_every_payload_source_is_tracked_and_not_a_symlink(self):
        for source, _mode in builder.FILES.values():
            with self.subTest(source=source):
                path = builder.ROOT / source
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())


if __name__ == "__main__":
    unittest.main()
