#!/usr/bin/env python3

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "ubuntu/t630-waydroid-software-profile"
CONFIG_HELPER = ROOT / "ubuntu/t630-waydroid-profile-config.py"
SPEC = importlib.util.spec_from_file_location("t630_waydroid_profile_config", CONFIG_HELPER)
config_helper = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(config_helper)


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
        self.assertIn("android wm size 1024x623", text)
        self.assertIn('"$config" apply', text)
        self.assertIn("t630-software-profile.enabled", text)
        self.assertIn("enforce)", text)

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

    def test_config_dimensions_apply_idempotently_and_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "waydroid.cfg"
            state = root / "state.json"
            lock = root / "lock"
            config.write_text(
                "[waydroid]\narch = arm64\n\n[properties]\n"
                "persist.waydroid.height = 700\n", encoding="utf-8")
            uid = os.geteuid()
            config_helper.update("apply", config, state, lock, required_uid=uid)
            applied = config.read_text(encoding="utf-8")
            self.assertIn("persist.waydroid.width = 1024", applied)
            self.assertIn("persist.waydroid.height = 623", applied)
            saved = json.loads(state.read_text(encoding="utf-8"))
            self.assertIsNone(saved["properties"]["persist.waydroid.width"])
            self.assertEqual(saved["properties"]["persist.waydroid.height"], "700")
            config_helper.update("apply", config, state, lock, required_uid=uid)
            self.assertEqual(json.loads(state.read_text(encoding="utf-8")), saved)
            config_helper.update("restore", config, state, lock, required_uid=uid)
            restored = config.read_text(encoding="utf-8")
            self.assertNotIn("persist.waydroid.width", restored)
            self.assertIn("persist.waydroid.height = 700", restored)
            self.assertFalse(state.exists())

    def test_config_helper_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.write_text("[waydroid]\n\n[properties]\n", encoding="utf-8")
            config = root / "waydroid.cfg"
            config.symlink_to(outside)
            with self.assertRaises(RuntimeError):
                config_helper.update(
                    "apply", config, root / "state", root / "lock",
                    required_uid=os.geteuid())


if __name__ == "__main__":
    unittest.main()
