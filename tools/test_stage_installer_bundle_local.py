from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).with_name("stage_installer_bundle_local.py")
sys.path.insert(0, str(SCRIPT.parent))


class LocalInstallerStagingTests(unittest.TestCase):
    def test_local_stager_is_guarded_and_ram_only(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('STAGING = "/run/t630-installer"', text)
        self.assertIn("/run/ubuntu/", text)
        self.assertIn("androidboot.em.model=SM-T630", text)
        self.assertIn("PARTNAME=linuxroot", text)
        self.assertIn("134217728", text)
        self.assertIn("PARTNAME=userdata", text)
        self.assertIn("92700632", text)
        self.assertIn("MemAvailable", text)
        self.assertIn("nosuid,nodev,noexec", text)
        self.assertIn("sha256sum -c SHA256SUMS", text)
        self.assertIn("COPIED_FROM_LINUXROOT_TO_RAM_NO_DEVICE_WRITE", text)
        self.assertIn("install_staged_release.sh", text)
        self.assertIn("prepare_staged_install.sh", text)
        for forbidden in ("mkfs", "dd if=", "of=/dev/", "heimdall", "--apply"):
            self.assertNotIn(forbidden, text)

    def test_rejects_non_userdata_and_traversal_sources(self):
        import stage_installer_bundle_local as subject

        for source in ("/tmp/bundle", "/run/ubuntu/../tmp", "relative"):
            with self.assertRaises(ValueError):
                subject.staging_script(source)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", SCRIPT], check=True)


if __name__ == "__main__":
    unittest.main()
