#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


SOURCE = Path(__file__).with_name("assemble_release_root.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("assemble_release_root", SOURCE)
assembly = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(assembly)


class ReleaseAssemblyTests(unittest.TestCase):
    def root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "etc").mkdir()
        (root / "home").mkdir()
        (root / ".t630-offline-root").write_text(assembly.OFFLINE_MARKER)
        (root / "etc/os-release").write_text(
            'NAME="Ubuntu"\nID=ubuntu\nVERSION_ID="24.04"\n')
        (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
        (root / "etc/machine-id").write_text("")
        return directory, root

    def test_empty_marked_ubuntu_root_passes(self):
        directory, root = self.root()
        try:
            self.assertEqual(assembly.validate_root(root), root.resolve())
        finally:
            directory.cleanup()

    def test_live_root_and_identity_state_are_rejected(self):
        with self.assertRaises(ValueError):
            assembly.validate_root(Path("/"))
        directory, root = self.root()
        try:
            (root / "etc/passwd").write_text(
                "root:x:0:0:root:/root:/bin/bash\nowner:x:1000:1000::/home/owner:/bin/bash\n")
            with self.assertRaisesRegex(ValueError, "identity audit"):
                assembly.validate_root(root)
        finally:
            directory.cleanup()

    def test_symlinked_root_is_rejected(self):
        directory, root = self.root()
        link = root.parent / (root.name + "-link")
        try:
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "unsafe release root"):
                assembly.validate_root(link)
        finally:
            link.unlink(missing_ok=True)
            directory.cleanup()

    def test_package_set_is_complete_versioned_and_private(self):
        self.assertEqual(len(assembly.EXPECTED), 14)
        self.assertEqual(len(assembly.INSTALL_ORDER), 13)
        self.assertIn(assembly.META_PACKAGE, assembly.EXPECTED)
        for filename, (package, version, digest) in assembly.EXPECTED.items():
            self.assertTrue(filename.endswith(".deb"))
            self.assertTrue(package and version)
            self.assertEqual(len(digest), 64)
        private = assembly.EXPECTED["t630-stock-assets_1.0.1+dze3_arm64.deb"]
        self.assertEqual(private[1], "1.0.1+dze3")
        self.assertIn("t630-boot-runtime_0.1.0_all.deb", assembly.EXPECTED)
        self.assertIn("t630-polkit-runtime_0.1.0_arm64.deb", assembly.EXPECTED)
        self.assertIn("t630-login-runtime_0.1.0_arm64.deb", assembly.EXPECTED)
        self.assertIn("t630-camera-runtime_0.1.3_arm64.deb", assembly.EXPECTED)

    def test_missing_packages_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing or unsafe"):
                assembly.validate_packages(Path(directory))


if __name__ == "__main__":
    unittest.main()
