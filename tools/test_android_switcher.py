#!/usr/bin/env python3

import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_android_switcher.py"
SPEC = importlib.util.spec_from_file_location("build_android_switcher", BUILDER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AndroidSwitcherTest(unittest.TestCase):
    def test_manifest_has_no_network_or_privileged_permissions(self):
        manifest = (ROOT / "android-switcher/AndroidManifest.xml").read_text()
        self.assertNotIn("uses-permission", manifest)
        self.assertIn(".MainActivity", manifest)
        self.assertIn("android.intent.category.LAUNCHER", manifest)

    def test_app_invokes_only_fixed_root_helper(self):
        source = (ROOT / "android-switcher/src/org/codebooker/t630switcher/MainActivity.java").read_text()
        self.assertIn('"su", "-c", SWITCH_COMMAND', source)
        self.assertIn('"/data/adb/t630/switch-to-ubuntu"', source)
        self.assertIn('" --switch-and-reboot"', source)
        self.assertNotIn("Runtime.getRuntime", source)
        self.assertNotIn("INTERNET", source)
        self.assertIn("Restart into Ubuntu", source)

    def test_root_helper_writes_only_boot_and_rolls_back(self):
        source = (ROOT / "android-switcher/switch-to-ubuntu.sh").read_text()
        subprocess.run(["sh", "-n", ROOT / "android-switcher/switch-to-ubuntu.sh"], check=True)
        self.assertIn("of=\"$boot\"", source)
        for forbidden in ("of=/dev/block/by-name/recovery", "of=/dev/block/by-name/vbmeta",
                          "of=/dev/block/by-name/userdata", "of=/dev/block/by-name/metadata"):
            self.assertNotIn(forbidden, source)
        self.assertIn("UBUNTU_SWITCH_FAILED_RESTORING_ANDROID", source)
        self.assertIn("Ubuntu-BOOT-readback", source)
        self.assertIn("setprop sys.powerctl reboot", source)

    def test_root_helper_defaults_to_read_only_check(self):
        source = (ROOT / "android-switcher/switch-to-ubuntu.sh").read_text()
        self.assertIn('mode=${1:---check}', source)
        self.assertIn('--check|--switch-and-reboot', source)
        check_gate = source.index('if test "$mode" = --check; then')
        first_write = source.index('dd if="$boot" of="$rollback"')
        self.assertLess(check_gate, first_write)
        self.assertIn("UBUNTU_SWITCH_READY", source)

    def test_helper_pins_geometry_and_protected_hashes(self):
        source = (ROOT / "android-switcher/switch-to-ubuntu.sh").read_text()
        for value in ("21880832", "134217728", "156098560", "92700632"):
            self.assertIn(value, source)
        for partition in ("recovery", "vendor_boot", "dtbo", "vbmeta"):
            self.assertIn(f"by-name/{partition}", source)

    def test_builder_is_valid_python_and_uses_private_keystore_default(self):
        ast.parse(BUILDER.read_text())
        source = BUILDER.read_text()
        self.assertIn("private-t630-switcher-keystore.p12", source)
        self.assertIn("apksigner", source)
        self.assertIn("zipalign", source)


if __name__ == "__main__":
    unittest.main()
