from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("stage_dual_layout_boot_v2_recovery.sh")


class DualLayoutBootV2RecoveryTests(unittest.TestCase):
    def test_is_boot_only_and_has_rollback(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("/dev/sda19", text)
        self.assertNotIn("/dev/sda34", text)
        self.assertNotIn("/dev/sda35", text)
        self.assertIn("rollback_on_error", text)
        self.assertIn("check_neighbors", text)
        self.assertIn("READBACK_VERIFIED", text)

    def test_write_is_after_all_read_only_guards(self):
        text = SCRIPT.read_text(encoding="utf-8")
        guards = text.index("DUAL_LAYOUT_BOOT_V2_READY_NO_CHANGES")
        write = text.index('of=/dev/sda19')
        self.assertLess(guards, write)
        self.assertIn("--check|--write", text)


if __name__ == "__main__":
    unittest.main()
