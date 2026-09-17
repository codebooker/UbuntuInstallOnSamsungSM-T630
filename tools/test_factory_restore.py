#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest

import flash_factory_restore
import prepare_factory_restore


ROOT = Path(__file__).resolve().parents[1]


class FactoryRestoreTests(unittest.TestCase):
    def test_exact_wiping_payload_plan(self):
        entries = flash_factory_restore.expected_payloads()
        self.assertEqual(len(entries), 41)
        partitions = {item[3] for item in entries if item[3] is not None}
        self.assertEqual(len(partitions), 40)
        self.assertIn(("AP", "userdata.img.lz4", "userdata.img", "USERDATA"), entries)
        self.assertIn(("CSC", prepare_factory_restore.PIT_NAME,
                       prepare_factory_restore.PIT_NAME, None), entries)
        self.assertNotIn("HOME_CSC", prepare_factory_restore.PAYLOADS)

    def test_factory_identity_is_pinned(self):
        self.assertEqual(len(prepare_factory_restore.ARCHIVE_SHA256), 64)
        self.assertEqual(len(prepare_factory_restore.PIT_SHA256), 64)
        self.assertEqual(flash_factory_restore.AUTHORIZATION,
                         "ERASE SM-T630 LINUXROOT")

    def test_flash_never_disables_size_checks(self):
        text = (ROOT / "tools/flash_factory_restore.py").read_text()
        self.assertNotIn("--skip-size-check", text)
        self.assertIn('command.extend(["--repartition", "--pit", str(pit)])', text)
        self.assertIn("payload_only", text)

    def test_stock_gpt_restore_is_guarded_and_transactional(self):
        source = ROOT / "maintenance/restore-stock-gpt"
        subprocess.run(["sh", "-n", source], check=True)
        text = source.read_text()
        for required in (
            "RESTORE ORIGINAL SM-T630 GPT AND ERASE DUALBOOT LAYOUT",
            "gpt-live-before-stock-restore.bin",
            "STOCK_GPT_SPLIT_LAYOUT_ROLLBACK_APPLIED",
            "check_partition sda34 userdata 21880832 226918360",
            "partition 35 survived stock GPT restore",
            "mknod",
        ):
            self.assertIn(required, text)
        self.assertNotIn("mkfs", text)

    def test_download_reboot_helper_uses_restart2(self):
        text = (ROOT / "tools/reboot_to_download.c").read_text()
        self.assertIn("LINUX_REBOOT_CMD_RESTART2", text)
        self.assertIn('"download"', text)


if __name__ == "__main__":
    unittest.main()
