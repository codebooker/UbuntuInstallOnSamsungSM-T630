#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FirstBootUiTests(unittest.TestCase):
    def test_expected_ubuntu_setup_pages_exist(self):
        source = (ROOT / "ubuntu/t630-first-boot-ui.py").read_text()
        for page in (
            "Welcome to Ubuntu",
            "Accessibility",
            "Keyboard",
            "Connect to a network",
            "Create your account",
            "Time zone",
            "Privacy",
            "Ready to use Ubuntu",
        ):
            with self.subTest(page=page):
                self.assertIn(f'"{page}"', source)

    def test_password_is_not_a_process_argument_or_profile_field(self):
        ui = (ROOT / "ubuntu/t630-first-boot-ui.py").read_text()
        backend = (ROOT / "ubuntu/t630_first_boot.py").read_text()
        self.assertIn('input=secret + "\\n"', ui)
        self.assertNotIn('"--password"', ui)
        profile_body = backend[backend.index("class SetupProfile:"):backend.index("def validate_profile")]
        self.assertNotIn("password", profile_body.lower())

    def test_owner_marker_is_committed_after_nonsecret_profile(self):
        backend = (ROOT / "ubuntu/t630_first_boot.py").read_text()
        profile_write = backend.index('Path("/etc/t630/first-boot-profile.json")')
        owner_write = backend.index('write_atomic(owner_path, profile.username')
        self.assertLess(profile_write, owner_write)

    def test_fresh_install_enters_wizard_before_owner_resolution(self):
        launcher = (ROOT / "ubuntu/t630-desktop-autostart").read_text()
        wizard = launcher.index("if [ ! -e /etc/t630/owner ]")
        resolution = launcher.index("t630_account.py env")
        self.assertLess(wizard, resolution)
        self.assertIn("exec \"$0\" \"$@\"", launcher)

    def test_user_profile_is_applied_in_the_owner_session(self):
        session = (ROOT / "ubuntu/t630-gnome-session").read_text()
        profile = (ROOT / "ubuntu/t630-apply-user-profile.py").read_text()
        self.assertIn("t630-apply-user-profile.py", session)
        self.assertIn("resolve_owner", profile)
        self.assertIn("os.geteuid() != owner.uid", profile)
        self.assertIn("org.gnome.desktop.input-sources", profile)
        self.assertIn("org.gnome.system.location", profile)


if __name__ == "__main__":
    unittest.main()
