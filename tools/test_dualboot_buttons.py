#!/usr/bin/env python3

from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DualBootButtonsTest(unittest.TestCase):
    def test_dialog_is_valid_python_and_uses_only_guarded_command(self):
        source = (ROOT / "ubuntu/t630-switch-dialog.py").read_text()
        ast.parse(source)
        self.assertIn('"/usr/bin/sudo"', source)
        self.assertIn('"/usr/local/sbin/t630-switch-to-native-android"', source)
        self.assertIn('"--switch-and-reboot"', source)
        self.assertNotIn("shell=True", source)
        self.assertIn("Restart into Android", source)

    def test_sudoers_grants_only_exact_guarded_reboot_command(self):
        source = (ROOT / "ubuntu/t630-dualboot-sudoers").read_text()
        rules = [line for line in source.splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(rules), 1)
        self.assertEqual(
            rules[0],
            "%t630-owner ALL=(root) NOPASSWD: "
            "/usr/local/sbin/t630-switch-to-native-android --switch-and-reboot",
        )
        self.assertNotIn("ALL=(ALL)", source)

    def test_both_ubuntu_surfaces_open_confirmation(self):
        controls = (ROOT / "ubuntu/t630_controls.py").read_text()
        extension = (ROOT / "ubuntu/gnome-tablet-tools/extension.js").read_text()
        for source in (controls, extension):
            self.assertIn("Restart into Android", source)
            self.assertIn("t630-switch-dialog", source)


if __name__ == "__main__":
    unittest.main()
