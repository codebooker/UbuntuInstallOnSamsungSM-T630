#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("flash_accepted_android_boot_download_mode.sh")


class AcceptedAndroidDownloadFlashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_default_is_read_only_and_hash_is_external(self):
        self.assertIn('mode=${1:---check}', self.text)
        self.assertIn('T630_ANDROID_BOOT_SHA256', self.text)
        self.assertIn('LOCAL_ARTIFACT_VERIFIED_NO_DEVICE_WRITE', self.text)

    def test_live_pit_limits_flash_to_boot(self):
        self.assertIn('Identifier: 19', self.text)
        self.assertIn('Partition Block Count: 24576', self.text)
        self.assertIn('Partition Name: BOOT', self.text)
        self.assertIn('flash --BOOT "$image" --resume', self.text)
        for forbidden in ('--VBMETA', '--RECOVERY', '--USERDATA', '--repartition'):
            self.assertNotIn(forbidden, self.text)

    def test_requires_exact_authorization(self):
        self.assertIn('FLASH ACCEPTED ANDROID BOOT TO SM-T630', self.text)


if __name__ == "__main__":
    unittest.main()
