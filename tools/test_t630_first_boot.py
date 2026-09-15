import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


UBUNTU = Path(__file__).parents[1] / "ubuntu"
sys.path.insert(0, str(UBUNTU))
SPEC = importlib.util.spec_from_file_location("t630_first_boot", UBUNTU / "t630_first_boot.py")
setup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)


class FirstBootTests(unittest.TestCase):
    def zoneinfo(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "America").mkdir()
        (root / "America/New_York").write_text("TZif", encoding="ascii")
        return directory, root

    def profile(self, **changes):
        values = dict(
            username="jack",
            full_name="Jack Example",
            hostname="ubuntu-tab",
            timezone="America/New_York",
            locale="en_US.UTF-8",
            keyboard_layout="us",
            location_services=False,
            large_text=False,
            high_contrast=False,
            screen_reader=False,
        )
        values.update(changes)
        return setup.SetupProfile(**values)

    def test_valid_profile_and_password(self):
        directory, zones = self.zoneinfo()
        try:
            setup.validate_profile(self.profile(), zones)
            setup.validate_password("correct horse battery staple")
        finally:
            directory.cleanup()

    def test_rejects_unsafe_identity_fields(self):
        directory, zones = self.zoneinfo()
        try:
            cases = (
                self.profile(username="root"),
                self.profile(username="Jack"),
                self.profile(full_name="Jack:root"),
                self.profile(hostname="-tablet"),
                self.profile(hostname="12345"),
                self.profile(locale="C"),
                self.profile(keyboard_layout="us;id"),
                self.profile(timezone="../etc/passwd"),
            )
            for profile in cases:
                with self.subTest(profile=profile), self.assertRaises(setup.SetupError):
                    setup.validate_profile(profile, zones)
        finally:
            directory.cleanup()

    def test_rejects_missing_or_escaping_timezone(self):
        directory, zones = self.zoneinfo()
        outside = Path(directory.name).parent / "outside-zone"
        outside.write_text("TZif", encoding="ascii")
        try:
            with self.assertRaises(setup.SetupError):
                setup.validate_profile(self.profile(timezone="America/Missing"), zones)
            (zones / "America/Escape").symlink_to(outside)
            with self.assertRaises(setup.SetupError):
                setup.validate_profile(self.profile(timezone="America/Escape"), zones)
        finally:
            outside.unlink(missing_ok=True)
            directory.cleanup()

    def test_rejects_short_or_multiline_password(self):
        for password in ("short", "eightchr\nsecond", "x" * 1025):
            with self.subTest(password=password[:12]), self.assertRaises(setup.SetupError):
                setup.validate_password(password)

    def test_command_plan_never_contains_password(self):
        with mock.patch.object(setup.grp, "getgrnam", side_effect=KeyError), \
             mock.patch.object(setup.grp, "getgrall", return_value=[]):
            commands = setup.command_plan(self.profile(), account_exists=False)
        rendered = repr(commands)
        self.assertIn("groupadd", rendered)
        self.assertIn("useradd", rendered)
        self.assertIn("usermod", rendered)
        self.assertNotIn("password", rendered.lower())

    def test_owner_group_and_only_existing_optional_groups_are_selected(self):
        groups = [type("Group", (), {"gr_name": name}) for name in ("audio", "sudo", "other")]
        with mock.patch.object(setup.grp, "getgrall", return_value=groups):
            self.assertEqual(setup.groups_for_owner(), ["t630-owner", "audio", "sudo"])

    def test_atomic_writer_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "etc/t630/owner"
            setup.write_atomic(target, "jack\n", 0o600)
            self.assertEqual(target.read_text(), "jack\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_machine_identity_must_be_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "machine-id"
            with mock.patch.object(setup, "run_checked") as run:
                target.write_text("0123456789abcdef0123456789abcdef\n", encoding="ascii")
                setup.initialize_machine_identity(target)
                run.assert_called_once_with(["/usr/bin/systemd-machine-id-setup"])
                for invalid in ("", "0123\n", "G" * 32 + "\n", "a" * 32):
                    target.write_text(invalid, encoding="ascii")
                    with self.assertRaises(setup.SetupError):
                        setup.initialize_machine_identity(target)


if __name__ == "__main__":
    unittest.main()
