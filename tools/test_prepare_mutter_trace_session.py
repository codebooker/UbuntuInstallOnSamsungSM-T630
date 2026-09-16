from pathlib import Path
import unittest
import subprocess

import prepare_mutter_trace_session as session


class MutterTraceSessionTests(unittest.TestCase):
    def setUp(self):
        self.base = (Path(__file__).resolve().parents[1] /
                     'ubuntu/t630-gnome-session').read_bytes()
        self.hashes = {name: 'a' * 64 for name in session.ARTIFACTS}

    def test_manual_session_keeps_auth_and_uses_no_proximity_preload(self):
        result = session.generate(self.base, self.hashes).decode()
        self.assertIn('test "${T630_MUTTER_PEN_TRACE:-0}" = 1', result)
        self.assertIn('test "${T630_PEN_METADATA_TRIAL:-0}" = 1', result)
        self.assertIn('export LD_LIBRARY_PATH=' + session.DIRECTORY, result)
        self.assertEqual(result.count('sha256sum ' + session.DIRECTORY), 11)
        self.assertIn('export GI_TYPELIB_PATH=' + session.DIRECTORY + '/typelibs', result)
        self.assertNotIn('t630-pen-floating-trial.so', result)
        self.assertNotIn('t630-pen-x11-metadata --refresh', result)
        self.assertIn('/usr/local/libexec/t630-lock-on-start', result)
        self.assertIn('export LD_PRELOAD=/usr/local/lib/t630-cogl-sync.so', result)
        self.assertNotIn('T630_MUTTER_PEN_TRACE', self.base.decode())
        subprocess.run(['sh', '-n'], input=result, text=True, check=True,
                       capture_output=True, timeout=5)

    def test_unknown_bases_libraries_and_injection_are_rejected(self):
        for hashes in ({}, {**self.hashes, 'unexpected.so': 'a' * 64},
                       {name: 'a' * 64 for name in session.LIBRARIES},
                       {**self.hashes, session.LIBRARIES[0]: '$(command)'},
                       {**self.hashes, session.LIBRARIES[0]: None}):
            with self.assertRaises(ValueError):
                session.generate(self.base, hashes)
        with self.assertRaises(ValueError):
            session.generate(self.base + b'\n', self.hashes)

    def test_source_trial_requires_additional_flag_and_keeps_lock(self):
        result = session.generate(self.base, self.hashes, source_trial=True).decode()
        self.assertIn('test "${T630_X11_PEN_FIX:-0}" = 1', result)
        self.assertIn('export T630_X11_PEN_FIX', result)
        self.assertIn('/usr/local/libexec/t630-lock-on-start', result)
        self.assertNotIn('T630_X11_PEN_FIX', session.generate(self.base, self.hashes).decode())
        subprocess.run(['sh', '-n'], input=result, text=True, check=True,
                       capture_output=True, timeout=5)
