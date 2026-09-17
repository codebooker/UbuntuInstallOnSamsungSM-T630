#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("stage_stock_recovery_wipe.sh")


class StageStockRecoveryWipeTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_pins_exact_wipe_bcb_and_authorization(self):
        self.assertIn(
            "bb26630239e7af8c098b4b0ed44074e29181ad4f7b28f73e726913afad948c89",
            self.text,
        )
        self.assertIn(
            "INITIALIZE SM-T630 NATIVE ANDROID USERDATA WITH STOCK RECOVERY",
            self.text,
        )

    def test_requires_host_backups_of_misc_and_metadata(self):
        self.assertIn("HOST_SAVED_MISC_SHA256", self.text)
        self.assertIn("HOST_SAVED_METADATA_SHA256", self.text)
        self.assertIn("host-misc-backup", self.text)
        self.assertIn("host-metadata-backup", self.text)
        self.assertIn(
            "7b3509a9165c9ec966ae06e7937997d283db8ddd0c478283446981fe847ee4ab",
            self.text,
        )

    def test_writes_only_misc_bcb_and_verifies_tail(self):
        self.assertIn('of="$misc" bs=2048 count=1 conv=notrunc,fsync', self.text)
        self.assertIn('test "$(tail_hash "$misc")" = "$original_tail"', self.text)
        self.assertNotIn("of=/dev/sda25", self.text)
        self.assertNotIn("of=/dev/sda34", self.text)
        self.assertNotIn("of=/dev/sda35", self.text)

    def test_validates_target_and_ubuntu_partition(self):
        self.assertIn('PARTNAME=linuxroot', self.text)
        self.assertIn('PARTNAME=userdata', self.text)
        self.assertIn('findmnt -n -o SOURCE /', self.text)
        self.assertIn('userdata is not blank', self.text)
        self.assertIn('userdata has a recognized filesystem', self.text)

    def test_has_full_misc_rollback(self):
        self.assertIn('of="$misc" bs=1048576 count=1 conv=fsync', self.text)
        self.assertIn("STOCK_RECOVERY_WIPE_MISC_ROLLBACK_VERIFIED", self.text)

    def test_pins_all_protected_images(self):
        for device in ("/dev/sda19", "/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(device, self.text)


if __name__ == "__main__":
    unittest.main()
