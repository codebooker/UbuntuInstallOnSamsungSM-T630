from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("prepare_staged_install.sh")


class PrepareStagedInstallTests(unittest.TestCase):
    def test_shell_syntax_and_exact_partition_guards(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)
        text = SCRIPT.read_text(encoding="utf-8")
        for value in (
                "PARTNAME=linuxroot", "134217728", "PARTNAME=userdata",
                "92700632", "/dev/sda34", "/run/t630-installer"):
            self.assertIn(value, text)

    def test_only_exact_chroot_processes_are_signalled(self):
        text = SCRIPT.read_text(encoding="utf-8")
        kill = text.index('kill -TERM "${proc##*/}"')
        exact_root = text.rindex('readlink "$proc/root"', 0, kill)
        self.assertLess(exact_root, kill)
        self.assertNotIn("kill -KILL", text)
        self.assertNotIn("pkill", text)

    def test_unmount_is_orderly_and_preserves_ram_stage(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('umount "$root"', text)
        self.assertNotIn("umount -l", text)
        self.assertNotIn("umount -f", text)
        self.assertNotIn("reboot", text)
        self.assertNotIn("poweroff", text)
        self.assertIn("RAM_PRESERVED", text)


if __name__ == "__main__":
    unittest.main()
