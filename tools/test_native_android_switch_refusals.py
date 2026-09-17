#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("check_native_android_switch_refusals.sh")


class NativeAndroidSwitchRefusalsTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_uses_private_mount_namespaces_and_read_only_switch_mode(self):
        self.assertEqual(self.text.count("unshare -m sh -c"), 3)
        self.assertEqual(self.text.count("--check\n"), 3)
        self.assertNotIn("--write", self.text)
        self.assertNotIn("--switch-and-reboot", self.text)

    def test_injects_expected_failure_classes(self):
        self.assertIn("accepted-android-boot hash mismatch", self.text)
        self.assertIn("external power is required", self.text)
        self.assertIn("recovery hash mismatch", self.text)
        self.assertIn("battery/status", self.text)
        self.assertIn("/run/ubuntu/dev/sda20", self.text)

    def test_rechecks_boot_and_every_protected_neighbor(self):
        for device in ("/dev/sda19", "/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(device, self.text)
        self.assertIn("SWITCH_REFUSAL_GATES_PASSED_NO_PERSISTENT_CHANGES", self.text)


if __name__ == "__main__":
    unittest.main()
