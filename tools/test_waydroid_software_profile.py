#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "ubuntu/t630-waydroid-software-profile"


class WaydroidSoftwareProfileTests(unittest.TestCase):
    def test_script_is_valid_and_device_scoped(self):
        subprocess.run(["sh", "-n", PROFILE], check=True)
        text = PROFILE.read_text(encoding="utf-8")
        self.assertIn("SM-T630-T630XXSBDZE3-Ubuntu-v1", text)
        self.assertIn('test "$(id -u)" = 0', text)

    def test_profile_uses_accepted_dimensions_and_zero_animations(self):
        text = PROFILE.read_text(encoding="utf-8")
        self.assertIn("persist.waydroid.width 1024", text)
        self.assertIn("persist.waydroid.height 623", text)
        for key in (
            "window_animation_scale",
            "transition_animation_scale",
            "animator_duration_scale",
        ):
            self.assertIn(f"{key} 0.0", text)

    def test_profile_is_reversible_and_validates_saved_values(self):
        text = PROFILE.read_text(encoding="utf-8")
        self.assertIn("t630-software-profile.before", text)
        self.assertIn("validate_value", text)
        self.assertIn("restore)", text)
        self.assertIn('rm -f "$state"', text)

    def test_profile_does_not_touch_accounts_or_app_data(self):
        text = PROFILE.read_text(encoding="utf-8")
        self.assertNotIn("/data/data", text)
        self.assertNotIn("pm disable", text)
        self.assertNotIn("accounts", text.lower())


if __name__ == "__main__":
    unittest.main()
