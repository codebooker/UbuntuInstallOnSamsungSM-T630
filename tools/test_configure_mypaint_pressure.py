import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import configure_mypaint_pressure as pressure


class MyPaintPressurePreferencesTests(unittest.TestCase):
    def test_main_guards_precede_any_settings_write(self):
        owner = SimpleNamespace(home='/home/example', uid=1000)
        account = SimpleNamespace(resolve_owner=lambda: owner)
        expected = '/home/example/.config/t630-gnome-preview'
        cases = ((0, expected, '2.0.1-10build2', False),
                 (1001, expected, '2.0.1-10build2', False),
                 (1000, '/wrong/config', '2.0.1-10build2', False),
                 (1000, expected, 'unsupported', False),
                 (1000, expected, '2.0.1-10build2', True))
        for uid, config_home, version, live in cases:
            with self.subTest(uid=uid, config_home=config_home, version=version, live=live), \
                 patch.dict(pressure.sys.modules, {'t630_account': account}), \
                 patch.dict(pressure.os.environ, {'XDG_CONFIG_HOME': config_home}), \
                 patch.object(pressure.sys, 'argv', ['configure']), \
                 patch.object(pressure.os, 'getuid', return_value=uid), \
                 patch.object(pressure.subprocess, 'check_output', return_value=version), \
                 patch.object(pressure, 'running_mypaint', return_value=live), \
                 patch.object(pressure, 'configure') as configure:
                with self.assertRaises(SystemExit):
                    pressure.main()
                configure.assert_not_called()

    def test_zero_preserved_and_identity_available(self):
        self.assertEqual(pressure.curve(0.5), [[0, 1], [0.5, 0], [1, 0]])
        self.assertEqual(pressure.curve(1.0), [[0, 1], [1, 0]])
        for invalid in (0, 0.19, 1.1, True, '0.5', None, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                pressure.curve(invalid)

    def test_preferences_preserved_with_exact_backup(self):
        with tempfile.TemporaryDirectory(prefix='t630-mypaint-pressure-') as directory:
            path = Path(directory) / 'mypaint/settings.json'
            path.parent.mkdir()
            old = b'{"input.global_pressure_mapping": [[0,1],[1,0]], "chosen": "keep"}\n'
            path.write_bytes(old)
            backup = pressure.configure(path, 0.5)
            self.assertEqual(backup.read_bytes(), old)
            result = json.loads(path.read_bytes())
            self.assertEqual(result['chosen'], 'keep')
            self.assertEqual(result[pressure.KEY], pressure.curve(0.5))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_json_and_symlinks_are_not_replaced(self):
        with tempfile.TemporaryDirectory(prefix='t630-mypaint-pressure-') as directory:
            path = Path(directory) / 'settings.json'
            for invalid in (b'[]', b'not-json'):
                path.write_bytes(invalid)
                with self.assertRaises(ValueError):
                    pressure.configure(path, 0.5)
                self.assertEqual(path.read_bytes(), invalid)
            link = Path(directory) / 'link.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                pressure.configure(link, 0.5)
            self.assertEqual(path.read_bytes(), b'not-json')

    def test_only_the_exact_running_owner_app_blocks_changes(self):
        with tempfile.TemporaryDirectory(prefix='t630-mypaint-proc-') as directory:
            root = Path(directory)
            proc = root / '123'
            proc.mkdir()
            cmdline = proc / 'cmdline'
            cmdline.write_bytes(b'/usr/bin/python3\0/tmp/mypaint-note.py\0')
            self.assertFalse(pressure.running_mypaint(root))
            cmdline.write_bytes(b'/usr/bin/python3\0/usr/local/libexec/t630-mypaint\0')
            self.assertTrue(pressure.running_mypaint(root))
            cmdline.write_bytes(b'/usr/bin/python3\0/run/trial/probe_mypaint_latency_v2.py\0')
            self.assertTrue(pressure.running_mypaint(root))
            cmdline.write_bytes(b'/usr/bin/python3\0/run/trial/probe_mypaint_latency.py\0')
            self.assertTrue(pressure.running_mypaint(root))

    def test_new_preference_file_has_no_backup(self):
        with tempfile.TemporaryDirectory(prefix='t630-mypaint-pressure-') as directory:
            path = Path(directory) / 'mypaint/settings.json'
            self.assertIsNone(pressure.configure(path, 0.5))
            self.assertEqual(json.loads(path.read_bytes()), {pressure.KEY: pressure.curve(0.5)})
