#!/usr/bin/env python3

from pathlib import Path
import unittest


SOURCE = Path(__file__).with_name("apply_stock_wipe_dualboot_split.py")


class ApplyStockWipeDualbootSplitHostTest(unittest.TestCase):
    def setUp(self):
        self.text = SOURCE.read_text()

    def test_requires_exact_phrase_and_new_backup(self):
        self.assertIn(
            "ERASE SM-T630 FACTORY USERDATA AND CREATE DUALBOOT SPLIT",
            self.text,
        )
        self.assertIn("host GPT backup path must be new", self.text)

    def test_exports_and_downloads_gpt_before_authorization(self):
        export = self.text.index("result = link.run(BACKUP_SCRIPT")
        download = self.text.index("link.download_ram")
        marker = self.text.index("HOST_SAVED_GPT_SHA256=")
        token = self.text.index("link.upload_ram((PHRASE")
        apply = self.text.index("sh {REMOTE_TOOL} --apply")
        self.assertLess(export, download)
        self.assertLess(download, marker)
        self.assertLess(marker, token)
        self.assertLess(token, apply)

    def test_pins_factory_geometry_and_gpt_backup_size(self):
        for value in ("248799232", "21880832", "226918360", "6656"):
            self.assertIn(value, self.text)
        self.assertIn("test ! -e /sys/class/block/sda35/uevent", self.text)


if __name__ == "__main__":
    unittest.main()
