from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/build_t630_polkit_runtime.sh"
PATCH = ROOT / "patches/polkit-gnome-t630-process-agent.patch"


class PolkitRuntimeBuildTests(unittest.TestCase):
    def test_builder_is_pinned_non_installing_and_owner_neutral(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)
        text = SCRIPT.read_text()
        self.assertIn("policykit-1-gnome_0.105.orig.tar.xz", text)
        self.assertIn("1784494963b8bf9a00eedc6cd3a2868f", text)
        self.assertIn("dpkg-divert", text)
        self.assertIn("Depends: polkitd,", text)
        self.assertNotIn("dpkg -i", text)
        patch = PATCH.read_text()
        self.assertIn("caller_uid < 1000", patch)
        self.assertIn("target_stat.st_uid != caller_uid", patch)
        self.assertNotIn("getuid () != 1000", patch)

    def test_dbus_service_drops_privileges_before_start(self):
        service = (ROOT / "ubuntu/org.freedesktop.PolicyKit1.service").read_text()
        self.assertIn("User=polkitd", service)
        self.assertIn("setpriv --no-new-privs", service)


if __name__ == "__main__":
    unittest.main()
