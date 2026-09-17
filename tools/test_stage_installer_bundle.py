from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name("stage_installer_bundle.py")


class InstallerStagingTests(unittest.TestCase):
    def test_stager_is_ram_only_and_exact_device_guarded(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('STAGING = "/run/t630-installer"', text)
        self.assertIn("androidboot.em.model=SM-T630", text)
        self.assertIn("PARTNAME=linuxroot", text)
        self.assertIn("134217728", text)
        self.assertIn("PARTNAME=userdata", text)
        self.assertIn("92700632", text)
        self.assertIn("MemAvailable", text)
        self.assertIn("tmpfs", text)
        self.assertIn("sha256sum -c SHA256SUMS", text)
        self.assertIn("INSTALLER_BUNDLE_VERIFIED_IN_RAM_NO_DEVICE_WRITE", text)
        self.assertIn("install_staged_release.sh", text)
        self.assertIn("prepare_staged_install.sh", text)
        self.assertIn("INSTALLER_CHECK_PASSED_LINUXROOT_UNMOUNTED_NO_DEVICE_WRITE", text)
        for forbidden in ("mkfs", "dd if=", "of=/dev/", "heimdall", "--write"):
            self.assertNotIn(forbidden, text)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", SCRIPT], check=True)

    def test_large_file_transfer_is_streamed(self):
        serial = SCRIPT.with_name("serial_link.py").read_text(encoding="utf-8")
        method = serial.split("def upload_file_ram", 1)[1].split(
            "def download_ram", 1)[0]
        self.assertIn("while chunk := stream.read", method)
        self.assertNotIn("read_bytes", method)
        self.assertIn("4 * 1024 * 1024 * 1024", method)


if __name__ == "__main__":
    unittest.main()
