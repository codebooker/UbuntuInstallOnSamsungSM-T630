import io
import importlib.util
import lzma
from pathlib import Path
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).with_name("build_first_boot_deb.py")
SPEC = importlib.util.spec_from_file_location("build_first_boot_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def read_ar(data: bytes) -> dict[str, bytes]:
    if not data.startswith(b"!<arch>\n"):
        raise AssertionError("not an ar archive")
    offset = 8
    members = {}
    while offset < len(data):
        header = data[offset : offset + 60]
        if len(header) != 60 or header[58:] != b"`\n":
            raise AssertionError("invalid ar header")
        name = header[:16].decode().strip().removesuffix("/")
        size = int(header[48:58].decode().strip())
        offset += 60
        members[name] = data[offset : offset + size]
        offset += size + (size % 2)
    return members


class FirstBootPackageTests(unittest.TestCase):
    def build_once(self, directory: Path, name: str) -> bytes:
        output = directory / name
        builder.build(output, 1_700_000_000)
        return output.read_bytes()

    def test_package_is_reproducible_and_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = self.build_once(directory, "first.deb")
            second = self.build_once(directory, "second.deb")
            self.assertEqual(first, second)

            members = read_ar(first)
            self.assertEqual(
                list(members),
                ["debian-binary", "control.tar.xz", "data.tar.xz"],
            )
            self.assertEqual(members["debian-binary"], b"2.0\n")

            with tarfile.open(
                fileobj=io.BytesIO(lzma.decompress(members["data.tar.xz"])),
                mode="r:",
            ) as archive:
                regular = {item.name.removeprefix("./"): item for item in archive if item.isfile()}
                self.assertEqual(set(regular), set(builder.FILES))
                self.assertEqual(regular["usr/local/libexec/t630-first-boot"].mode, 0o755)
                self.assertEqual(
                    regular[
                        "usr/share/doc/t630-first-boot/examples/first-boot-profile.json"
                    ].mode,
                    0o644,
                )

    def test_control_declares_runtime_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = self.build_once(Path(temporary), "package.deb")
            control_archive = lzma.decompress(read_ar(data)["control.tar.xz"])
            with tarfile.open(fileobj=io.BytesIO(control_archive), mode="r:") as archive:
                control = archive.extractfile("./control").read().decode()
            self.assertIn("Package: t630-first-boot\n", control)
            self.assertIn("Architecture: all\n", control)
            self.assertIn("python3-gi", control)
            self.assertIn("systemd", control)
            self.assertNotIn("Password:", control)

    def test_payload_never_contains_owner_state(self):
        forbidden = {"etc/t630/owner", "etc/machine-id", "root/.ssh/authorized_keys"}
        self.assertTrue(forbidden.isdisjoint(builder.FILES))

    def test_wifi_helper_uses_network_picker_and_system_keyboard(self):
        helper = (builder.ROOT / "ubuntu/connect_wifi.py").read_text()
        self.assertIn("Gtk.ComboBoxText.new_with_entry()", helper)
        self.assertIn("Refresh networks", helper)
        self.assertIn("'SSID,SIGNAL'", helper)
        self.assertNotIn("self.keyboard", helper)
        self.assertIn("LOCK_EX | fcntl.LOCK_NB", helper)
        self.assertIn("window.password.grab_focus()", helper)
        self.assertIn("Path('/sys/class/net/wlan0')", helper)
        self.assertIn("802-11-wireless.mac-address", helper)
        self.assertIn("f'/sys/class/net/{interface}/address'", helper)
        self.assertIn("except (OSError, subprocess.SubprocessError):\n                        pass", helper)
        self.assertNotIn("GENERAL.HWADDR", helper)

    def test_first_boot_embeds_wifi_in_the_existing_wizard_surface(self):
        wizard = (builder.ROOT / "ubuntu/t630-first-boot-ui.py").read_text()
        self.assertIn("self.wifi_password", wizard)
        self.assertIn("def connect_wifi_worker", wizard)
        self.assertIn("self.wifi_password.grab_focus()", wizard)
        self.assertNotIn("subprocess.Popen", wizard)
        self.assertIn('Path("/sys/class/net/wlan0")', wizard)
        self.assertIn("802-11-wireless.mac-address", wizard)
        self.assertIn("Association and DHCP", wizard)
        self.assertNotIn("GENERAL.HWADDR", wizard)


if __name__ == "__main__":
    unittest.main()
