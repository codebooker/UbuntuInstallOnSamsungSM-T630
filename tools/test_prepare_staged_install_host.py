from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("prepare_staged_install.py")


class PrepareStagedInstallHostTests(unittest.TestCase):
    def test_orderly_prepare_precedes_read_only_check(self):
        text = SCRIPT.read_text(encoding="utf-8")
        prepare = text.index('link.run(f"sh {PREPARE}"')
        check = text.index('link.run(f"sh {INSTALLER} --check"')
        self.assertLess(prepare, check)
        self.assertNotIn("--apply", text)
        self.assertIn("NO_DEVICE_WRITE", text)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", SCRIPT], check=True)


if __name__ == "__main__":
    unittest.main()
