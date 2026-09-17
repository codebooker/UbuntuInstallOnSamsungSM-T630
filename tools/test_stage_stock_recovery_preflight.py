#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


SOURCE = Path(__file__).with_name("stage_stock_recovery_preflight.sh")


class StageStockRecoveryPreflightTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_pins_non_wiping_bcb_and_misc_backup(self):
        self.assertIn("b0b0993da05a79506348c702de750e300e866532b20a6024c2e85aa5350e0957", self.text)
        self.assertIn("HOST_SAVED_MISC_SHA256", self.text)
        self.assertIn("live-misc", self.text)
        self.assertIn("BOOT STOCK RECOVERY FOR READ ONLY DUALBOOT PREFLIGHT", self.text)
        self.assertNotIn("--wipe_data", self.text)

    def test_only_first_bcb_bytes_are_written_and_tail_is_verified(self):
        self.assertIn('of="$misc" bs=2048 count=1 conv=notrunc,fsync', self.text)
        self.assertIn('test "$(tail_hash "$misc")" = "$original_tail"', self.text)
        self.assertNotIn("of=/dev/sda34", self.text)
        self.assertNotIn("of=/dev/sda35", self.text)

    def test_defaults_to_read_only_check_before_the_first_write(self):
        self.assertIn('mode=${1:---check}', self.text)
        self.assertIn('--check|--stage', self.text)
        self.assertIn('STOCK_RECOVERY_PREFLIGHT_READY_NO_CHANGES', self.text)
        check_gate = self.text.index('if test "$mode" = --check; then')
        first_write = self.text.index('of="$misc" bs=2048 count=1')
        self.assertLess(check_gate, first_write)

    def test_rollback_restores_full_misc(self):
        self.assertIn('of="$misc" bs=1048576 count=1 conv=fsync', self.text)
        self.assertIn("STOCK_RECOVERY_MISC_ROLLBACK_VERIFIED", self.text)

    def test_pins_boot_recovery_and_split_geometry(self):
        for device in ("/dev/sda19", "/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(device, self.text)
        self.assertIn("PARTNAME=linuxroot", self.text)
        self.assertIn("PARTNAME=userdata", self.text)
        self.assertIn("92700632", self.text)


if __name__ == "__main__":
    unittest.main()
