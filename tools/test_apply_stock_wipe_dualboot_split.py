#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "maintenance/apply-stock-wipe-dualboot-split"


class ApplyStockWipeDualbootSplitTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_busybox_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_requires_destructive_factory_authorization(self):
        self.assertIn("AUTHORIZE-FACTORY-USERDATA-WIPE-AND-SPLIT", self.text)
        self.assertIn(
            "ERASE SM-T630 FACTORY USERDATA AND CREATE DUALBOOT SPLIT",
            self.text,
        )

    def test_accepts_only_exact_factory_userdata(self):
        self.assertIn("Stock Android exposes /data through dm-default-key", self.text)
        self.assertIn("test \"$ext4_magic\" != 53ef", self.text)
        self.assertIn("use the preserving split flow", self.text)
        self.assertIn("partition 35 already exists", self.text)
        self.assertIn("226918360", self.text)
        self.assertIn("Partition name: 'userdata'", self.text)

    def test_pins_geometry_and_preserves_userdata_guid(self):
        self.assertIn("--new=34:2735104:19512319", self.text)
        self.assertIn("--new=35:19512320:31099898", self.text)
        self.assertIn('--partition-guid=34:"$unique"', self.text)
        self.assertIn("134217728", self.text)
        self.assertIn("92700632", self.text)

    def test_requires_host_verified_backup_and_rolls_back(self):
        self.assertIn("HOST-VERIFIED-GPT-BACKUP", self.text)
        self.assertIn("live GPT differs from host-saved backup", self.text)
        self.assertIn('--load-backup="$backup"', self.text)
        self.assertIn("STOCK_SPLIT_GPT_AUTO_ROLLBACK_APPLIED", self.text)

    def test_never_formats_or_resizes_a_partition(self):
        self.assertNotIn("mkfs", self.text)
        self.assertNotIn("mke2fs", self.text)
        self.assertNotIn("resize2fs", self.text)
        self.assertNotIn("e2fsck", self.text)

    def test_protected_partitions_are_hash_pinned(self):
        for device in ("sda20", "sda21", "sda22", "sde19"):
            self.assertIn(device, self.text)
        self.assertIn(
            "9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e",
            self.text,
        )
        self.assertIn(
            "2bf7a057399c1b2cae374ae6ec56e972d87a12441a2c49998b7cd43d370c5741",
            self.text,
        )

    def test_requires_power_and_unmounted_new_partitions(self):
        self.assertIn("external power is required", self.text)
        self.assertIn('if is_mounted sda34; then fail "linuxroot is mounted"', self.text)
        self.assertIn('if is_mounted sda35; then fail "userdata is mounted"', self.text)


if __name__ == "__main__":
    unittest.main()
