#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("restore_ubuntu_boot_download_mode.sh")


class RestoreUbuntuBootDownloadModeTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_pins_accepted_ubuntu_boot(self):
        self.assertIn(
            "eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb",
            self.text,
        )
        self.assertIn("100663296", self.text)

    def test_requires_exact_live_pit_boot_entry(self):
        self.assertIn("Identifier: 19", self.text)
        self.assertIn("Partition Block Count: 24576", self.text)
        self.assertIn("Partition Name: BOOT", self.text)
        self.assertIn("download-pit", self.text)

    def test_flashes_only_boot_without_size_bypass_or_repartition(self):
        self.assertIn('flash --BOOT "$image" --resume', self.text)
        self.assertNotIn("--skip-size-check", self.text)
        self.assertNotIn("--repartition", self.text)
        for forbidden in ("--RECOVERY", "--VBMETA", "--USERDATA", "--MISC"):
            self.assertNotIn(forbidden, self.text)

    def test_write_requires_exact_authorization(self):
        self.assertIn("RESTORE ACCEPTED UBUNTU BOOT TO SM-T630", self.text)
        self.assertIn("--check|--write", self.text)


if __name__ == "__main__":
    unittest.main()
