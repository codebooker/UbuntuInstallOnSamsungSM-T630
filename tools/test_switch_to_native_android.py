#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("switch_to_native_android.sh")


class SwitchToNativeAndroidTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_pins_both_boot_images_and_writes_only_boot(self):
        self.assertIn("android_hash_file=$artifact/boot.sha256", self.text)
        self.assertIn('test "${#android_boot}" = 64', self.text)
        self.assertIn('check_hash "$android_boot" "$image" accepted-android-boot', self.text)
        self.assertIn("eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb", self.text)
        self.assertIn("of=/dev/sda19", self.text)
        self.assertNotIn("of=/dev/sda25", self.text)
        self.assertNotIn("of=/dev/sda34", self.text)
        self.assertNotIn("of=/dev/sda35", self.text)

    def test_treats_post_boot_userdata_as_ciphertext(self):
        self.assertIn("RAW USERDATA IS CIPHERTEXT", self.text)
        self.assertIn("userdata unexpectedly exposes plaintext F2FS", self.text)
        self.assertNotIn("fsck.f2fs", self.text)
        self.assertIn("dm-default-key", self.text)

    def test_has_no_write_check_mode_and_exact_authorization(self):
        self.assertIn("NATIVE_ANDROID_ENCRYPTED_INSTALLATION_READY_NO_CHANGES", self.text)
        self.assertIn("SWITCH SM-T630 FROM ACCEPTED UBUNTU TO ACCEPTED NATIVE ANDROID", self.text)
        self.assertIn("--switch-and-reboot", self.text)
        self.assertIn("t630-display power restart", self.text)

    def test_rolls_back_to_accepted_ubuntu_boot(self):
        self.assertIn("NATIVE_ANDROID_SWITCH_FAILED_RESTORING_UBUNTU", self.text)
        self.assertIn('check_hash "$android_boot" /dev/sda19 Android-BOOT-readback', self.text)
        self.assertIn("NATIVE_ANDROID_SWITCH_ROLLBACK_VERIFIED", self.text)

    def test_pins_protected_neighbors_and_geometry(self):
        for device in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(device, self.text)
        self.assertIn("156098560", self.text)
        self.assertIn("92700632", self.text)


if __name__ == "__main__":
    unittest.main()
