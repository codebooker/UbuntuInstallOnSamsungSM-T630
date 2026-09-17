from pathlib import Path
import subprocess
import unittest

import authorize_staged_install as subject


class AuthorizeInstallTests(unittest.TestCase):
    def test_exact_confirmation_and_recovery_acknowledgement_are_required(self):
        text = Path(subject.__file__).read_text(encoding="utf-8")
        self.assertEqual(subject.PHRASE, "ERASE SM-T630 LINUXROOT")
        self.assertEqual(subject.TOKEN,
                         "ERASE SM-T630 LINUXROOT /dev/sda34 134217728")
        self.assertIn("Android userdata is a separate guarded partition", text)
        self.assertIn("--acknowledge-stock-recovery", text)
        self.assertIn("if input(\"> \") != PHRASE", text)
        self.assertIn("nothing was changed", text)

    def test_check_runs_before_token_and_apply(self):
        text = Path(subject.__file__).read_text(encoding="utf-8")
        check = text.index('f"sh {INSTALLER} --check"')
        token = text.index("INSTALLER_ERASE_TOKEN_CREATED_ONCE")
        apply = text.index('f"sh {INSTALLER} --apply"')
        self.assertLess(check, token)
        self.assertLess(token, apply)
        self.assertIn("set -C", text)
        self.assertIn("INSTALLER_APPLY_COMPLETE_ROOT_VERIFIED_REBOOT_REQUIRED", text)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", subject.__file__], check=True)


if __name__ == "__main__":
    unittest.main()
