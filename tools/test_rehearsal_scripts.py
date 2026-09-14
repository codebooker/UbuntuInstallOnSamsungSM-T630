from pathlib import Path
import subprocess
import unittest


TOOLS = Path(__file__).parent


class RehearsalScriptTests(unittest.TestCase):
    def test_shell_scripts_are_valid_and_refuse_missing_root(self):
        for name in ("provision_rehearsal_root.sh", "check_rehearsal_root.sh"):
            path = TOOLS / name
            with self.subTest(script=name):
                subprocess.run(["sh", "-n", path], check=True)
                result = subprocess.run(
                    ["sh", path], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)

    def test_offline_service_policy_denies_start(self):
        result = subprocess.run(["sh", TOOLS / "rehearsal-policy-rc.d"])
        self.assertEqual(result.returncode, 101)

    def test_provisioner_sanitizes_identity_after_apt(self):
        text = (TOOLS / "provision_rehearsal_root.sh").read_text()
        apt = text.index("apt-get install")
        machine_id = text.index('truncate -s 0 "$root/etc/machine-id"')
        audit = text.rindex("audit_release_root.py")
        self.assertLess(apt, machine_id)
        self.assertLess(machine_id, audit)
        self.assertIn('rm -f -- "$root/var/lib/dbus/machine-id"', text)
        self.assertIn('rm -f -- "$root/usr/sbin/policy-rc.d"', text)

    def test_checker_covers_release_and_mount_state(self):
        text = (TOOLS / "check_rehearsal_root.sh").read_text()
        self.assertIn("t630-release-base", text)
        self.assertIn("t630-boot-runtime", text)
        self.assertIn("t630-polkit-runtime", text)
        self.assertIn("usr/bin/maliit-keyboard", text)
        self.assertIn("dpkg --root=", text)
        self.assertIn("native_linkage: valid", text)
        self.assertIn("mount_leaks: none", text)


if __name__ == "__main__":
    unittest.main()
