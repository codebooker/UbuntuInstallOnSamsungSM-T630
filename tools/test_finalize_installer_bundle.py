import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import finalize_installer_bundle as subject


class InstallerBundleTests(unittest.TestCase):
    def bundle(self, root: Path):
        (root / "boot").mkdir()
        rootfs = root / "t630-release-rootfs.tar.gz"
        rootfs.write_bytes(b"rootfs")
        root_record = {
            "status": "LOCAL_PRIVATE_INSTALLER_INPUT_DO_NOT_REDISTRIBUTE",
            "model": "SM-T630", "stock_build": "T630XXSBDZE3",
            "archive": rootfs.name, "archive_bytes": rootfs.stat().st_size,
            "archive_sha256": hashlib.sha256(b"rootfs").hexdigest(),
            "contains_proprietary_stock_assets": True,
            "contains_human_account": False,
            "contains_network_credentials": False,
        }
        (root / "t630-release-rootfs.tar.gz.manifest.json").write_text(
            json.dumps(root_record), encoding="utf-8")
        boot = root / "boot/boot.img"
        boot.write_bytes(b"boot")
        boot_record = {
            "model": "SM-T630", "stock_build": "T630XXSBDZE3",
            "root_uuid": subject.ROOT_UUID, "boot_bytes": 4,
            "boot_sha256": hashlib.sha256(b"boot").hexdigest(),
            "kernel_sha256": subject.EXPECTED_KERNEL_SHA256,
        }
        (root / "boot/manifest.json").write_text(
            json.dumps(boot_record), encoding="utf-8")

    def accepted(self, root: Path):
        return mock.patch.multiple(
            subject, EXPECTED_BOOT_BYTES=4,
            EXPECTED_BOOT_SHA256=hashlib.sha256(b"boot").hexdigest())

    def test_valid_inputs_are_sealed_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.bundle(root)
            with self.accepted(root):
                record = subject.finalize(root)
            self.assertEqual(record["status"],
                             "PRIVATE_INSTALLER_BUNDLE_SEALED_NOT_DEVICE_WRITE_AUTHORIZATION")
            self.assertEqual((root / "installer-bundle.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / "SHA256SUMS").stat().st_mode & 0o777, 0o600)
            with self.accepted(root):
                verified = subject.verify_sealed(root)
            self.assertEqual(verified["files"], record["files"])
            with self.accepted(root):
                with self.assertRaisesRegex(ValueError, "overwrite a sealed bundle"):
                    subject.finalize(root)

    def test_modified_rootfs_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.bundle(root)
            (root / "t630-release-rootfs.tar.gz").write_bytes(b"changed")
            with self.accepted(root):
                with self.assertRaisesRegex(ValueError, "rootfs manifest content mismatch"):
                    subject.validate(root)

    def test_unaccepted_boot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.bundle(root)
            with self.assertRaisesRegex(ValueError, "physically accepted v12"):
                subject.validate(root)

    def test_changed_checksum_seal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.bundle(root)
            with self.accepted(root):
                subject.finalize(root)
            (root / "SHA256SUMS").write_text("invalid\n", encoding="ascii")
            with self.accepted(root):
                with self.assertRaisesRegex(ValueError, "SHA256SUMS differs"):
                    subject.verify_sealed(root)


if __name__ == "__main__":
    unittest.main()
