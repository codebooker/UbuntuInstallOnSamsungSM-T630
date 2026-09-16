from pathlib import Path
import subprocess
import tempfile
import unittest

import build_installer_runtime as subject


class InstallerRuntimeTests(unittest.TestCase):
    def test_ldd_parser_requires_loader_and_rejects_missing(self):
        output = """\
libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x1)
/lib/ld-linux-aarch64.so.1 (0x2)
"""
        self.assertEqual(subject.ldd_paths(output), {
            "/lib/aarch64-linux-gnu/libc.so.6",
            "/lib/ld-linux-aarch64.so.1",
        })
        with self.assertRaisesRegex(ValueError, "unresolved"):
            subject.ldd_paths("libacl.so.1 => not found")
        with self.assertRaisesRegex(ValueError, "loader"):
            subject.ldd_paths("libc.so.6 => /lib/libc.so.6 (0x1)")

    def test_safe_source_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root.parent / (root.name + "-outside")
            outside.write_bytes(b"x")
            try:
                (root / "escape").symlink_to(outside)
                with self.assertRaisesRegex(ValueError, "escapes root"):
                    subject.safe_source(root, "/escape")
            finally:
                outside.unlink(missing_ok=True)

    def test_builder_source_is_arm64_host_only_and_has_no_device_io(self):
        path = Path(subject.__file__)
        text = path.read_text(encoding="utf-8")
        self.assertEqual(subject.BINARIES,
                         ("/usr/sbin/mke2fs", "/usr/sbin/e2fsck", "/usr/bin/tar",
                          "/usr/bin/dpkg-query"))
        self.assertIn("ARM64 ELF64", text)
        self.assertIn("validate_installed_root", text)
        self.assertIn("PRIVATE_INSTALLER_RUNTIME_ARM64_NO_DEVICE_WRITE", text)
        for forbidden in ("/dev/sda", "mkfs.ext4", "dd if=", "heimdall"):
            self.assertNotIn(forbidden, text)

    def test_python_syntax(self):
        subprocess.run(["python3", "-m", "py_compile", subject.__file__], check=True)


if __name__ == "__main__":
    unittest.main()
