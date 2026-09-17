#!/usr/bin/env python3

from pathlib import Path
import tempfile
import unittest
from unittest import mock

import provision_private_dualboot_assets as subject


class PrivateDualbootAssetsTest(unittest.TestCase):
    def test_provisions_private_assets_without_acceptance_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "root"
            root.mkdir()
            android = base / "android.img"
            ubuntu = base / "ubuntu.img"
            android.write_bytes(b"a")
            ubuntu.write_bytes(b"u")
            hashes = {android: "a" * 64, ubuntu: subject.UBUNTU_BOOT_SHA256}
            with (mock.patch.object(subject.os, "geteuid", return_value=0),
                  mock.patch.object(subject, "validate_root", return_value=root),
                  mock.patch.object(subject, "checked_boot",
                                    side_effect=lambda path, _label: (path, hashes[path])),
                  mock.patch.object(subject, "digest",
                                    side_effect=lambda path: hashes.get(path, (
                                        "a" * 64 if path.name == "boot.img" else
                                        subject.UBUNTU_BOOT_SHA256)))):
                record = subject.provision(root, android, ubuntu)
            artifact = root / "opt/t630/artifacts/native-android-stock"
            self.assertEqual((artifact / "boot.sha256").read_text(), "a" * 64 + "\n")
            self.assertEqual((artifact / "AUTHORIZE-NATIVE-ANDROID-SWITCH").read_text(),
                             subject.AUTHORIZATION)
            self.assertFalse((root / "etc/t630/native-android-accepted").exists())
            self.assertFalse(record["acceptance_marker_created"])

    def test_stock_android_boot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            image = Path(directory) / "image"
            image.write_bytes(b"x")
            values = iter((subject.STOCK_ANDROID_BOOT_SHA256, subject.UBUNTU_BOOT_SHA256))
            with (mock.patch.object(subject.os, "geteuid", return_value=0),
                  mock.patch.object(subject, "validate_root", return_value=root),
                  mock.patch.object(subject, "checked_boot",
                                    side_effect=lambda *_args: (image, next(values)))):
                with self.assertRaisesRegex(ValueError, "stock"):
                    subject.provision(root, image, image)


if __name__ == "__main__":
    unittest.main()
