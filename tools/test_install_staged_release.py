from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("install_staged_release.sh")


class StagedInstallerTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)

    def test_read_only_check_precedes_authorization_and_format(self):
        text = SCRIPT.read_text(encoding="utf-8")
        check = text.index("INSTALLER_CHECK_PASSED_LINUXROOT_UNMOUNTED_NO_DEVICE_WRITE")
        authorization = text.index('test -f "$authorization"')
        format_call = text.index('"$runtime/usr/sbin/mke2fs" -t ext4')
        self.assertLess(check, authorization)
        self.assertLess(authorization, format_call)
        self.assertIn("--check|--apply", text)
        self.assertIn("ERASE SM-T630 LINUXROOT /dev/sda34 134217728", text)
        self.assertIn('test ! -e "$started"', text)
        self.assertIn('if [ ! -e "$runtime" ]', text)
        self.assertIn('test -d "$runtime" && test ! -L "$runtime"', text)

    def test_exact_device_and_protected_partition_guards(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for value in (
                "androidboot.em.model=SM-T630", "PARTNAME=linuxroot", "PARTN=34",
                "259:18", "134217728", "PARTNAME=userdata", "PARTN=35",
                "92700632", "/dev/sda19", "/dev/sda20",
                "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(value, text)
        self.assertIn('fail "linuxroot is mounted"', text)
        self.assertIn('fail "linuxroot has block holders"', text)
        self.assertNotIn('device=/dev/sda35', text)
        self.assertIn(
            "a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225",
            text)
        self.assertIn(
            "9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e",
            text)

    def test_root_validation_precedes_success(self):
        text = SCRIPT.read_text(encoding="utf-8")
        format_call = text.index('"$runtime/usr/sbin/mke2fs" -t ext4')
        extraction = text.index("--numeric-owner --same-owner --acls --xattrs")
        package = text.index("t630-release-base")
        fsck = text.index('"$runtime/usr/sbin/e2fsck" -fn')
        success = text.index("INSTALLER_APPLY_COMPLETE_ROOT_VERIFIED_REBOOT_REQUIRED")
        self.assertLess(format_call, extraction)
        self.assertLess(extraction, package)
        self.assertLess(package, fsck)
        self.assertLess(fsck, success)

    def test_boot_partition_is_verified_not_written(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"$boot_hash" /dev/sda19 | sha256sum -c -', text)
        self.assertNotIn("of=/dev/sda19", text)
        self.assertNotIn("heimdall", text)


if __name__ == "__main__":
    unittest.main()
