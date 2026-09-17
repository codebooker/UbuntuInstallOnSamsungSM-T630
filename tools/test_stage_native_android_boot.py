#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("stage_native_android_boot.sh")


class StageNativeAndroidBootTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_writes_only_boot_with_exact_images(self):
        self.assertIn("79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796", self.text)
        self.assertIn("eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb", self.text)
        self.assertIn('of=/dev/sda19', self.text)
        self.assertNotIn('of=/dev/sda34', self.text)
        self.assertNotIn('of=/dev/sda35', self.text)

    def test_requires_recovery_initialized_android_storage(self):
        self.assertIn("userdata is not F2FS", self.text)
        self.assertIn("metadata is not ext4", self.text)
        self.assertIn("fsck.f2fs --dry-run", self.text)
        self.assertIn("misc still contains a boot command", self.text)

    def test_has_full_boot_rollback_and_readback(self):
        self.assertIn("NATIVE_ANDROID_BOOT_FAILED_RESTORING_UBUNTU", self.text)
        self.assertIn('check_hash "$android_boot" /dev/sda19 Android-BOOT-readback', self.text)
        self.assertIn("WRITE EXACT DZE3 STOCK ANDROID BOOT TO SM-T630", self.text)

    def test_protected_neighbors_are_pinned(self):
        for device in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(device, self.text)


if __name__ == "__main__":
    unittest.main()
