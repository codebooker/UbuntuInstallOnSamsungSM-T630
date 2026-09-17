#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "android-switcher/update-installed-switcher.sh"
HOST = ROOT / "tools/update_android_switch_payload.py"


class AndroidSwitchPayloadUpdateTest(unittest.TestCase):
    def test_android_updater_never_writes_a_partition(self):
        subprocess.run(["sh", "-n", UPDATER], check=True)
        text = UPDATER.read_text()
        self.assertNotIn("dd ", text)
        self.assertNotIn("of=/dev/", text)
        self.assertIn("ANDROID_SWITCH_PAYLOAD_V2_READY_NO_CHANGES", text)
        self.assertIn("ANDROID_SWITCH_PAYLOAD_V2_INSTALLED_NO_PARTITION_WRITE", text)
        self.assertIn("installed-android-boot", text)
        self.assertIn("stale update files exist", text)

    def test_host_defaults_to_check_and_uses_fixed_sources(self):
        subprocess.run(["python3", "-m", "py_compile", HOST], check=True)
        text = HOST.read_text()
        self.assertIn('parser.add_argument("--apply"', text)
        self.assertIn('mode = "--apply" if apply else "--check"', text)
        self.assertIn("output/dual-layout-ubuntu-v2/boot.img", text)
        self.assertIn("android-switcher/switch-to-ubuntu.sh", text)
        self.assertNotIn("shell=True", text)


if __name__ == "__main__":
    unittest.main()
