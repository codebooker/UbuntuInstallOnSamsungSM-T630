#!/usr/bin/env python3

from pathlib import Path
import ast
import unittest


SOURCE = Path(__file__).with_name("initialize_native_android_userdata.py")


class InitializeNativeAndroidUserdataTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_python_parses(self):
        ast.parse(self.text)

    def test_requires_new_host_backup_directory_and_exact_authorization(self):
        self.assertIn("backup directory must not already exist", self.text)
        self.assertIn("exact recovery-wipe authorization is required", self.text)
        self.assertIn("INITIALIZE SM-T630 NATIVE ANDROID USERDATA WITH STOCK RECOVERY", self.text)

    def test_downloads_full_misc_and_metadata_before_staging(self):
        self.assertIn("bs=1048576 count=1", self.text)
        self.assertIn("bs=1048576 count=16", self.text)
        self.assertIn('link.download_ram(REMOTE["misc"]', self.text)
        self.assertIn('link.download_ram(REMOTE["metadata"]', self.text)

    def test_runs_no_write_gate_before_optional_stage(self):
        check = self.text.index('t630-stage-stock-recovery-wipe.sh --check')
        stage = self.text.index('t630-stage-stock-recovery-wipe.sh --stage')
        self.assertLess(check, stage)
        self.assertIn('"--stage" if apply else "--check"', self.text)

    def test_never_formats_or_writes_data_partitions(self):
        self.assertNotIn("mkfs", self.text)
        self.assertNotIn("of=/dev/sda25", self.text)
        self.assertNotIn("of=/dev/sda34", self.text)
        self.assertNotIn("of=/dev/sda35", self.text)


if __name__ == "__main__":
    unittest.main()
