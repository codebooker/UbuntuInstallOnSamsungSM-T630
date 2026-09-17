#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest

import t630_installer_gui as subject


class T630InstallerGuiTest(unittest.TestCase):
    def test_safe_tablet_stage_command(self):
        command, stdin = subject.command_for(
            "tablet", "/run/ubuntu/opt/t630/bundle", "stage", False)
        self.assertEqual(command[-2:], [
            "--tablet-bundle", "/run/ubuntu/opt/t630/bundle"])
        self.assertIsNone(stdin)
        self.assertNotIn("--install", command)

    def test_host_verify_command(self):
        command, stdin = subject.command_for("host", "/bundle", "verify", False)
        self.assertEqual(command[-3:], ["--host-bundle", "/bundle", "--verify-only"])
        self.assertIsNone(stdin)

    def test_install_requires_acknowledgement_and_passes_exact_phrase(self):
        with self.assertRaisesRegex(ValueError, "deeply verified"):
            subject.command_for("tablet", "/bundle", "install", False)
        command, stdin = subject.command_for("tablet", "/bundle", "install", True)
        self.assertIn("--acknowledge-stock-recovery", command)
        self.assertEqual(stdin, subject.ERASE_PHRASE + "\n")

    def test_staged_prepare_does_not_recopy_bundle(self):
        command, stdin = subject.command_for("staged", "", "prepare", False)
        self.assertEqual(command[-2:], ["--staged", "--prepare"])
        self.assertIsNone(stdin)

    def test_invalid_action_combinations_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Verify only"):
            subject.command_for("tablet", "/bundle", "verify", False)
        with self.assertRaisesRegex(ValueError, "already staged"):
            subject.command_for("staged", "", "stage", False)

    def test_gui_never_uses_a_shell_or_contains_device_writes(self):
        text = Path(subject.__file__).read_text()
        self.assertIn("subprocess.Popen", text)
        self.assertNotIn("shell=True", text)
        for forbidden in ("/dev/sda", "mkfs", "dd if=", "--apply"):
            self.assertNotIn(forbidden, text)

    def test_import_does_not_create_a_window_and_python_parses(self):
        subprocess.run(["python3", "-m", "py_compile", subject.__file__], check=True)

    def test_double_click_launcher_only_starts_the_gui(self):
        launcher = Path(subject.__file__).resolve().parents[1] / \
            "Launch SM-T630 Installer.command"
        text = launcher.read_text()
        subprocess.run(["sh", "-n", launcher], check=True)
        self.assertIn("tools/t630_installer_gui.py", text)
        for forbidden in ("--install", "--prepare", "/dev/", "sudo"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
