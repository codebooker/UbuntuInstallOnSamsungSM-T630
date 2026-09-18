#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("flash_dualboot_maintenance_download_mode.sh")


class DualbootMaintenanceDownloadFlashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_default_is_read_only_and_artifact_is_hash_pinned(self):
        self.assertIn("mode=${1:---check}", self.text)
        self.assertIn(
            "c45e960fcbc6a30ab98872529d27a157a41409ea7601166330956b7f6e74ea4e",
            self.text,
        )
        self.assertIn("LOCAL_ARTIFACT_VERIFIED_NO_DEVICE_WRITE", self.text)

    def test_live_pit_limits_flash_to_boot(self):
        self.assertIn("Identifier: 19", self.text)
        self.assertIn("Partition Block Count: 24576", self.text)
        self.assertIn("Partition Name: BOOT", self.text)
        self.assertIn('flash --BOOT "$image" --resume', self.text)
        for forbidden in ("--VBMETA", "--RECOVERY", "--USERDATA", "--repartition"):
            self.assertNotIn(forbidden, self.text)

    def test_requires_exact_authorization(self):
        self.assertIn("FLASH RAM MAINTENANCE BOOT TO SM-T630", self.text)


if __name__ == "__main__":
    unittest.main()
