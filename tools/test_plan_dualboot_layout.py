#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_dualboot_layout", ROOT / "tools/plan_dualboot_layout.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DualbootLayoutTest(unittest.TestCase):
    def test_reviewed_64_gib_split(self):
        plan = MODULE.plan_layout(
            disk_sectors=248_799_232,
            current_start=21_880_832,
            current_sectors=226_918_360,
            ubuntu_gib=64,
            minimum_ext4_blocks=9_836_055,
            ext4_block_bytes=4096,
        )
        self.assertEqual(plan["status"], "PLAN_ONLY_NO_DEVICE_WRITES")
        self.assertEqual(plan["sysfs_linuxroot_start"], 21_880_832)
        self.assertEqual(plan["sysfs_linuxroot_end"], 156_098_559)
        self.assertEqual(plan["sysfs_userdata_start"], 156_098_560)
        self.assertEqual(plan["sysfs_userdata_end"], 248_799_191)
        self.assertEqual(plan["gpt_linuxroot_start"], 2_735_104)
        self.assertEqual(plan["gpt_linuxroot_end"], 19_512_319)
        self.assertEqual(plan["gpt_userdata_start"], 19_512_320)
        self.assertEqual(plan["gpt_userdata_end"], 31_099_898)
        self.assertAlmostEqual(plan["userdata_gib"], 44.2031059265)
        self.assertGreater(plan["ext4_headroom_blocks"], 6_000_000)

    def test_rejects_target_below_filesystem_minimum(self):
        with self.assertRaisesRegex(ValueError, "ext4 minimum"):
            MODULE.plan_layout(
                disk_sectors=248_799_232,
                current_start=21_880_832,
                current_sectors=226_918_360,
                ubuntu_gib=32,
                minimum_ext4_blocks=9_836_055,
                ext4_block_bytes=4096,
            )

    def test_rejects_unaligned_start(self):
        with self.assertRaisesRegex(ValueError, "not 1 MiB aligned"):
            MODULE.plan_layout(
                disk_sectors=248_799_232,
                current_start=21_880_833,
                current_sectors=226_918_359,
                ubuntu_gib=64,
                minimum_ext4_blocks=9_836_055,
                ext4_block_bytes=4096,
            )


if __name__ == "__main__":
    unittest.main()
