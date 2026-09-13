#!/usr/bin/env python3
"""Isolated power/lock regressions; never touches the tablet's real devices."""
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

local = Path(__file__).resolve().parents[1] / 'ubuntu'
sys.path.insert(0, str(local))
source = local / 't630-power-button.py'
if not source.exists():
    source = Path('/usr/local/sbin/t630-power-button')
loader = importlib.machinery.SourceFileLoader('tablet_power_tests', str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
power = importlib.util.module_from_spec(spec)
loader.exec_module(power)


class PowerTests(unittest.TestCase):
    def test_only_successful_power_wake_requests_light(self):
        with mock.patch.object(power, 'Path') as paths, \
                mock.patch.object(power.subprocess, 'check_output') as run:
            paths.return_value.exists.return_value = True
            for result, expected in (
                ('{"slept":true,"power_wake":true}', True),
                ('{"slept":true,"power_wake":false}', False),
                ('{"slept":false,"power_wake":true}', False),
                ('{"slept":false,"reason":"policy disabled"}', False),
            ):
                with self.subTest(result=result):
                    run.return_value = result
                    self.assertEqual(power.manual_suspend(), expected)

    def test_missing_helper_or_policy_never_sleeps(self):
        with mock.patch.object(power, 'Path') as paths, \
                mock.patch.object(power.subprocess, 'check_output') as run:
            paths.return_value.exists.return_value = False
            self.assertFalse(power.manual_suspend())
            run.assert_not_called()

    def test_malformed_helper_result_raises_for_existing_recovery_path(self):
        with mock.patch.object(power, 'Path') as paths, \
                mock.patch.object(power.subprocess, 'check_output', return_value='bad json'):
            paths.return_value.exists.return_value = True
            with self.assertRaises(ValueError):
                power.manual_suspend()

    def display(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / 'max_brightness').write_text('306')
        (root / 'brightness').write_text('254')
        light = mock.patch.object(power, 'LIGHT', root)
        state = mock.patch.object(power, 'STATE', root / 'saved')
        light.start()
        state.start()
        self.addCleanup(light.stop)
        self.addCleanup(state.stop)
        return root

    def test_unconfirmed_gnome_lock_never_blanks(self):
        root = self.display()
        with mock.patch.object(power, 'screen', return_value='(false,)'), \
                mock.patch.object(power, 'locked_hint', return_value=True):
            with self.assertRaises(RuntimeError):
                power.lock_and_blank()
        self.assertEqual((root / 'brightness').read_text(), '254')
        self.assertFalse(power.STATE.exists())

    def test_unconfirmed_login_lock_never_blanks(self):
        root = self.display()
        with mock.patch.object(power, 'screen', return_value='(true,)'), \
                mock.patch.object(power, 'locked_hint', return_value=False):
            with self.assertRaises(RuntimeError):
                power.lock_and_blank()
        self.assertEqual((root / 'brightness').read_text(), '254')
        self.assertFalse(power.STATE.exists())

    def test_verified_blank_restore_never_sends_unlock(self):
        root = self.display()
        with mock.patch.object(power, 'screen', return_value='(true,)') as screen, \
                mock.patch.object(power, 'locked_hint', return_value=True):
            power.lock_and_blank()
            self.assertEqual((root / 'brightness').read_text(), '0')
            self.assertEqual(power.STATE.stat().st_mode & 0o777, 0o600)
            power.restore()
            self.assertEqual((root / 'brightness').read_text(), '254')
            self.assertFalse(power.STATE.exists())
            self.assertTrue(all(call.args == ('GetActive',) for call in screen.call_args_list))

    def test_bad_saved_brightness_is_not_applied(self):
        root = self.display()
        power.STATE.write_text('9999')
        with self.assertRaises(RuntimeError):
            power.restore()
        self.assertEqual((root / 'brightness').read_text(), '254')


if __name__ == '__main__':
    unittest.main()
