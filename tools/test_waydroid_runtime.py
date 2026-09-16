#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import io
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class WaydroidRuntimeTests(unittest.TestCase):
    def test_lxc_start_wrapper_enters_outer_mount_namespace(self):
        wrapper = ROOT / "ubuntu/t630-waydroid-lxc-start"
        subprocess.run(["sh", "-n", wrapper], check=True)
        text = wrapper.read_text()
        self.assertIn("--target 1 --mount --root=/proc/1/root", text)
        self.assertIn("/bin/unshare -m", text)
        self.assertIn("mount --make-rslave /", text)
        self.assertIn("mount --rbind /run/ubuntu /ubuntu", text)
        self.assertIn("mount --rbind /ubuntu/run /run", text)
        self.assertIn('exec /usr/bin/lxc-start "$@"', text)
        self.assertIn("SM-T630-T630XXSBDZE3-Ubuntu-v1", text)

    def test_prepare_uses_fixed_legacy_controllers_and_binderfs(self):
        prepare = ROOT / "ubuntu/t630-waydroid-prepare"
        subprocess.run(["sh", "-n", prepare], check=True)
        text = prepare.read_text()
        for item in ("cpu_cpuacct:cpu,cpuacct", "memory:memory",
                     "devices:devices", "freezer:freezer", "pids:pids"):
            self.assertIn(item, text)
        self.assertIn("mount -t binder binder /dev/binderfs", text)
        self.assertIn("binder hwbinder vndbinder", text)
        self.assertIn("container start", text)
        self.assertIn("/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin", text)
        self.assertIn('command -v lxc-start', text)

    def test_user_wrapper_selects_nested_gnome_socket(self):
        wrapper = ROOT / "ubuntu/t630-waydroid"
        subprocess.run(["sh", "-n", wrapper], check=True)
        text = wrapper.read_text()
        self.assertIn("WAYLAND_DISPLAY=t630-gnome-0", text)
        self.assertIn('exec "$real" "$@"', text)
        self.assertIn('if [ "$(id -u)" = 0 ]', text)

    def test_desktop_startup_prepares_waydroid_without_starting_android(self):
        startup = (ROOT / "ubuntu/t630-desktop-autostart").read_text()
        self.assertIn("/usr/local/sbin/t630-waydroid-prepare", startup)
        self.assertIn("/etc/t630/waydroid.disabled", startup)

    def test_runtime_package_is_reproducible_and_pins_dependencies(self):
        source = ROOT / "tools/build_waydroid_runtime_deb.py"
        spec = importlib.util.spec_from_file_location("waydroid_deb", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first.deb"
            second = Path(temp) / "second.deb"
            self.assertEqual(module.build(first, 0), module.build(second, 0))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            blob = first.read_bytes()
            offset = 8
            members = {}
            while offset < len(blob):
                header = blob[offset:offset + 60]
                name = header[:16].decode().strip().rstrip("/")
                size = int(header[48:58].decode().strip())
                start = offset + 60
                members[name] = blob[start:start + size]
                offset = start + size + (size % 2)
            with tarfile.open(
                fileobj=io.BytesIO(members["control.tar.xz"]), mode="r:xz"
            ) as archive:
                control = archive.extractfile("./control").read().decode()
            self.assertIn("Package: t630-waydroid-runtime\n", control)
            self.assertIn("waydroid (= 1.6.2)", control)
            self.assertIn("lxc (= 1:5.0.3-2ubuntu7.2)", control)
            self.assertIn("python3", control)
            with tarfile.open(
                fileobj=io.BytesIO(members["data.tar.xz"]), mode="r:xz"
            ) as archive:
                checker = archive.getmember(
                    "./usr/local/sbin/t630-check-waydroid-gapps"
                )
                self.assertEqual(checker.mode, 0o755)
                profile = archive.getmember(
                    "./usr/local/sbin/t630-waydroid-software-profile"
                )
                self.assertEqual(profile.mode, 0o755)


if __name__ == "__main__":
    unittest.main()
