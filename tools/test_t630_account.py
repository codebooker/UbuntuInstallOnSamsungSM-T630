import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "ubuntu" / "t630_account.py"
SPEC = importlib.util.spec_from_file_location("t630_account", MODULE_PATH)
account = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = account
SPEC.loader.exec_module(account)


def passwd(name="jack", uid=1000, gid=1000, home="/home/jack", shell="/bin/bash"):
    return SimpleNamespace(
        pw_name=name, pw_uid=uid, pw_gid=gid, pw_dir=home, pw_shell=shell
    )


class OwnerAccountTests(unittest.TestCase):
    def resolve(self, content="jack\n", entry=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owner"
            path.write_text(content, encoding="utf-8")
            with mock.patch.object(account.pwd, "getpwnam", return_value=entry or passwd()):
                return account.resolve_owner(path)

    def test_valid_account_comes_from_passwd_database(self):
        result = self.resolve()
        self.assertEqual(
            (result.username, result.uid, result.home),
            ("jack", 1000, "/home/jack"),
        )

    def test_rejects_shell_content_and_extra_lines(self):
        for content in ("jack;id\n", "jack\nroot\n", "jack", "Jack\n", "\n"):
            with self.subTest(content=content), self.assertRaises(account.AccountError):
                self.resolve(content)

    def test_rejects_missing_account(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "owner"
            path.write_text("missing\n", encoding="utf-8")
            with mock.patch.object(account.pwd, "getpwnam", side_effect=KeyError):
                with self.assertRaises(account.AccountError):
                    account.resolve_owner(path)

    def test_rejects_privileged_or_noninteractive_accounts(self):
        bad = (
            passwd(uid=0, gid=0, home="/root"),
            passwd(gid=999),
            passwd(home="/srv/jack"),
            passwd(shell="/usr/sbin/nologin"),
        )
        for entry in bad:
            with self.subTest(entry=entry), self.assertRaises(account.AccountError):
                self.resolve(entry=entry)

    def test_shell_environment_is_complete(self):
        with mock.patch.object(account, "resolve_locale", return_value="en_US.UTF-8"):
            result = account.shell_environment(
                account.OwnerAccount("jack", 1000, 1000, "/home/jack", "/bin/bash")
            )
        self.assertEqual(
            result,
            "T630_OWNER=jack\nT630_OWNER_UID=1000\n"
            "T630_OWNER_GID=1000\nT630_OWNER_HOME=/home/jack\n"
            "T630_LOCALE=en_US.UTF-8",
        )

    def test_locale_is_strict_and_fails_to_safe_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locale"
            for value, expected in (
                ("LANG=en_US.UTF-8\n", "en_US.UTF-8"),
                ('LANG="fr_FR.UTF-8"\n', "fr_FR.UTF-8"),
                ("LANG=C.UTF-8\n", "C.UTF-8"),
                ("LANG=$(id)\n", "C.UTF-8"),
                ("LANG=en_US.UTF-8\nLANG=fr_FR.UTF-8\n", "C.UTF-8"),
            ):
                with self.subTest(value=value):
                    path.write_text(value, encoding="utf-8")
                    self.assertEqual(account.resolve_locale(path), expected)

    def test_json_shape_has_no_secret_fields(self):
        payload = json.loads(json.dumps(account.asdict(self.resolve())))
        self.assertEqual(set(payload), {"username", "uid", "gid", "home", "shell"})
        self.assertNotIn("password", payload)


if __name__ == "__main__":
    unittest.main()
