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
        self.assertIn('new ProcessBuilder("su")', source)
        self.assertIn('writer.write("exec " + SWITCH_COMMAND + "\\n")', source)
        self.assertNotIn('"su", "-c"', source)
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
        for value in ("sda19", "98304", "sda34", "67108864", "sda35", "46350316"):
            self.assertIn(value, source)
        self.assertIn('readlink -f "$boot"', source)
        self.assertIn("/proc/partitions", source)
        self.assertIn("dumpsys battery", source)
        self.assertIn("ro.boot.boot_recovery", source)
        for partition in ("recovery", "vendor_boot", "dtbo", "vbmeta"):
            self.assertIn(f"by-name/{partition}", source)
        self.assertIn("a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225", source)
        self.assertIn("9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e", source)

    def test_helper_flushes_and_journals_durable_boot_handoff(self):
        source = (ROOT / "android-switcher/switch-to-ubuntu.sh").read_text()
        self.assertGreaterEqual(source.count('blockdev --flushbufs "$boot"'), 2)
        self.assertIn("Ubuntu-BOOT-durable-readback", source)
        self.assertIn("last-ubuntu-switch", source)
        durable = source.index("Ubuntu-BOOT-durable-readback")
        committed = source.index("committed=1", durable)
        reboot = source.index("setprop sys.powerctl reboot", committed)
        self.assertLess(durable, committed)
        self.assertLess(committed, reboot)

    def test_builder_is_valid_python_and_uses_private_keystore_default(self):
        ast.parse(BUILDER.read_text())
        source = BUILDER.read_text()
        self.assertIn("private-t630-switcher-keystore.p12", source)
        self.assertIn("apksigner", source)
        self.assertIn("zipalign", source)


if __name__ == "__main__":
    unittest.main()
