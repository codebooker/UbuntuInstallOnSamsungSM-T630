from pathlib import Path
import tempfile
import unittest
from unittest import mock

import build_release_archive as subject


class ReleaseArchiveTests(unittest.TestCase):
    def root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "etc").mkdir()
        (root / "home").mkdir()
        (root / "var/lib/dpkg").mkdir(parents=True)
        (root / ".t630-offline-root").write_text(
            "SM-T630 OFFLINE RELEASE ROOT\n", encoding="utf-8")
        (root / "etc/os-release").write_text(
            'ID=ubuntu\nVERSION_ID="24.04"\n', encoding="utf-8")
        (root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/bash\n", encoding="utf-8")
        (root / "etc/machine-id").write_text("", encoding="utf-8")
        (root / "etc/t630-install-id").write_text(
            "SM-T630-T630XXSBDZE3-Ubuntu-v1\n", encoding="utf-8")
        paragraphs = []
        for package, version, _digest in subject.EXPECTED.values():
            paragraphs.append(
                f"Package: {package}\nVersion: {version}\nStatus: install ok installed\n")
        (root / "var/lib/dpkg/status").write_text(
            "\n".join(paragraphs), encoding="utf-8")
        return temporary, root

    def test_complete_clean_root_passes(self):
        temporary, root = self.root()
        try:
            validated, versions = subject.validate_installed_root(root)
            self.assertEqual(validated, root.resolve())
            self.assertEqual(len(versions), len(subject.EXPECTED))
        finally:
            temporary.cleanup()

    def test_wrong_release_version_fails(self):
        temporary, root = self.root()
        try:
            status = root / "var/lib/dpkg/status"
            status.write_text(status.read_text().replace("Version: 0.1.15", "Version: 0.1.14"))
            with self.assertRaisesRegex(ValueError, "version mismatch"):
                subject.validate_installed_root(root)
        finally:
            temporary.cleanup()

    def test_human_account_fails_before_packaging(self):
        temporary, root = self.root()
        try:
            (root / "etc/passwd").write_text(
                "root:x:0:0:root:/root:/bin/bash\nowner:x:1000:1000::/home/owner:/bin/bash\n")
            with self.assertRaisesRegex(ValueError, "identity audit"):
                subject.validate_installed_root(root)
        finally:
            temporary.cleanup()

    def test_live_mount_below_root_fails(self):
        with mock.patch.object(
                subject.Path, "read_text",
                return_value="1 0 0:1 / /tmp/root/dev rw - tmpfs tmpfs rw\n"):
            with self.assertRaisesRegex(ValueError, "contains a live mount"):
                subject.reject_mounts(Path("/tmp/root"))


if __name__ == "__main__":
    unittest.main()
