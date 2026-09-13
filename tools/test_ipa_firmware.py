#!/usr/bin/env python3
import hashlib
import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

local = Path(__file__).resolve().parents[1] / 'ubuntu/t630-ipa-start.py'
module_path = local if local.exists() else Path('/usr/local/sbin/t630-ipa-start')
loader = importlib.machinery.SourceFileLoader('ipa_start', str(module_path))
spec = importlib.util.spec_from_loader(loader.name, loader)
ipa = importlib.util.module_from_spec(spec)
loader.exec_module(ipa)


class FirmwareValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture = {'b00': b'header', 'b01': b'signing', 'mdt': b'headersigning'}
        digests = {key: hashlib.sha256(value).hexdigest() for key, value in fixture.items()}
        self.override = patch.dict(ipa.HASHES, digests, clear=True)
        self.override.start()
        self.addCleanup(self.override.stop)
        for key, value in fixture.items():
            (self.root / ('yupik_ipa_fws.' + key)).write_bytes(value)

    def test_all_files_validate_with_metadata_last(self):
        files = ipa.validate_files(self.root)
        self.assertEqual(files[-1].suffix, '.mdt')
        self.assertEqual(len(files), 3)

    def test_wrong_signing_rejected(self):
        (self.root / 'yupik_ipa_fws.b01').write_bytes(b'wrong signing')
        with self.assertRaises(RuntimeError):
            ipa.validate_files(self.root)

    def test_missing_file_rejected(self):
        (self.root / 'yupik_ipa_fws.b00').unlink()
        with self.assertRaises(FileNotFoundError):
            ipa.validate_files(self.root)

    def test_symlink_source_rejected(self):
        target = self.root / 'yupik_ipa_fws.b01'
        target.rename(self.root / 'source')
        target.symlink_to(self.root / 'source')
        with self.assertRaises(RuntimeError):
            ipa.validate_files(self.root)


if __name__ == '__main__':
    unittest.main()
