#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "maintenance/apply-dualboot-split"


class ApplyDualbootSplitTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_busybox_shell_parses(self):
        subprocess.run(["sh", "-n", SOURCE], check=True)

    def test_has_two_distinct_tokens_and_phases(self):
        self.assertIn("--shrink)", self.text)
        self.assertIn("--split)", self.text)
        self.assertIn("SHRINK SM-T630 UBUNTU EXT4 TO 16777216 BLOCKS", self.text)
        self.assertIn("SPLIT SM-T630 PARTITION 34 AND CREATE PARTITION 35", self.text)
        self.assertIn("same-session shrink marker absent", self.text)

    def test_pins_exact_geometry_and_preserves_root_guid(self):
        self.assertIn("--new=34:2735104:19512319", self.text)
        self.assertIn("--new=35:19512320:31099898", self.text)
        self.assertIn("--partition-guid=34:\"$unique\"", self.text)
        self.assertIn("134217728", self.text)
        self.assertIn("92700632", self.text)

    def test_requires_host_verified_backup_and_has_automatic_rollback(self):
        self.assertIn("HOST-VERIFIED-GPT-BACKUP", self.text)
        self.assertIn("live GPT differs from host-saved backup", self.text)
        self.assertIn("--load-backup=\"$backup\"", self.text)
        self.assertIn("DUALBOOT_GPT_AUTO_ROLLBACK_APPLIED", self.text)

    def test_checks_filesystem_before_and_after_split(self):
        self.assertIn("resize2fs \"$rootdev\" \"$target_blocks\"", self.text)
        self.assertIn("e2fsck -fn \"$rootdev\"", self.text)
        self.assertIn("mount -t ext4 -o ro,noload", self.text)
        self.assertIn("t630-install-id", self.text)

    def test_never_formats_the_new_android_partition(self):
        self.assertNotIn("mkfs", self.text)
        self.assertNotIn("mke2fs", self.text)
        self.assertNotIn("resize2fs /dev/sda35", self.text)

    def test_protected_partitions_are_hash_pinned(self):
        for device in ("sda20", "sda21", "sda22", "sde19"):
            self.assertIn(device, self.text)

    def test_refreshes_device_nodes_after_partition_table_reread(self):
        self.assertIn("make_block_node sda34 \"$rootdev\"", self.text)
        self.assertIn("make_block_node sda35 \"$userdata_node\"", self.text)
        self.assertIn("/sys/class/block/$device/dev", self.text)


if __name__ == "__main__":
    unittest.main()
