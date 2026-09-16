import hashlib
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import probe_mypaint_gil_trial as probe


class MyPaintGilArtifactGuardsTests(unittest.TestCase):
    def test_non_ram_or_wrong_named_paths_refuse(self):
        for directory in (Path('/tmp/t630-mypaint-gil-trial-test'), Path('/run/other')):
            with self.assertRaises(ValueError):
                probe.validate(directory)

    def test_root_owned_exact_hash_and_regular_artifact_required(self):
        directory = Path('/run/t630-mypaint-gil-trial-test')
        content = b'fixture'
        expected = {'binding.py': hashlib.sha256(content).hexdigest()}
        folder = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)
        valid_file = SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_uid=0, st_size=len(content))
        with patch.object(Path, 'is_symlink', return_value=False), \
             patch.object(Path, 'stat', return_value=folder), \
             patch.object(Path, 'read_bytes', return_value=content), \
             patch.dict(probe.EXPECTED, expected, clear=True):
            with patch.object(Path, 'lstat', return_value=valid_file):
                probe.validate(directory)
                with patch.object(Path, 'read_bytes', return_value=b'wrong'):
                    with self.assertRaises(ValueError):
                        probe.validate(directory)
            for mode, uid in ((stat.S_IFLNK | 0o777, 0), (stat.S_IFREG | 0o666, 0),
                              (stat.S_IFREG | 0o644, 1000)):
                info = SimpleNamespace(st_mode=mode, st_uid=uid, st_size=4)
                with patch.object(Path, 'lstat', return_value=info):
                    with self.assertRaises(ValueError):
                        probe.validate(directory)

    def test_root_process_refuses_before_package_or_artifact_access(self):
        with patch.object(probe.sys, 'argv', ['probe', '--library-dir', '/run/test', '--threads', '4']), \
             patch.object(probe.os, 'getuid', return_value=0), \
             patch.object(probe.subprocess, 'check_output') as query:
            with self.assertRaises(SystemExit):
                probe.main()
            query.assert_not_called()
