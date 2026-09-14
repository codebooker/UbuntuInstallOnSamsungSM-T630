import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import prepare_rehearsal_root as subject


class PrepareRehearsalRootTests(unittest.TestCase):
    def test_destination_must_be_new(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "new, real directory"):
                subject.validate_destination(root)

    def test_destination_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            target = parent / "target"
            target.mkdir()
            link = parent / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "new, real directory"):
                subject.validate_destination(link)

    def test_archive_members_reject_parent_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                entry = tarfile.TarInfo("../escape")
                entry.size = 1
                output.addfile(entry, io.BytesIO(b"x"))
            with self.assertRaisesRegex(ValueError, "unsafe path"):
                subject.archive_members(archive)

    def test_prepare_rejects_wrong_digest_before_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            archive = parent / subject.ARCHIVE_NAME
            archive.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                subject.prepare(archive, parent / "root")
            self.assertFalse((parent / "root").exists())

    def test_failed_audit_removes_created_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            archive = parent / subject.ARCHIVE_NAME
            archive.write_bytes(b"test")
            destination = parent / "root"
            with (mock.patch.object(subject, "digest", return_value=subject.ARCHIVE_SHA256),
                  mock.patch.object(subject, "archive_members", return_value=["etc/"]),
                  mock.patch.object(subject.subprocess, "run"),
                  mock.patch.object(subject, "audit", return_value=["bad state"])):
                with self.assertRaisesRegex(ValueError, "failed identity audit"):
                    subject.prepare(archive, destination)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
