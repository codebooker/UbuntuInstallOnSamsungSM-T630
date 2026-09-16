from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("build_local_installer.sh")


class LocalInstallerWorkflowTests(unittest.TestCase):
    def test_workflow_is_host_only_and_fail_closed(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("/dev/sda", "mkfs", "heimdall", "dd if="):
            self.assertNotIn(forbidden, text)
        self.assertIn('test "$(id -u)" = 0', text)
        self.assertIn('test "$(uname -s)" = Linux', text)
        self.assertIn("work directory must not exist", text)
        self.assertIn("prepare_rehearsal_root.py", text)
        self.assertIn("assemble_release_root.py", text)
        self.assertIn("check_rehearsal_root.sh", text)
        self.assertIn("build_installer_runtime.py", text)
        self.assertIn("build_release_archive.py", text)
        self.assertIn("build_boot_persistent.py", text)
        self.assertIn("finalize_installer_bundle.py", text)

    def test_shell_syntax(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)


if __name__ == "__main__":
    unittest.main()
