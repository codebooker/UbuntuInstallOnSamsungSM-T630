#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


class NestedTouchResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'nested_touch_reset', Path(__file__).with_name('reset_nested_touch.py'))
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def run_reset(self, args=(), contacts=0, disabled=False, fail_disable=False):
        calls = []

        def xinput(command, **kwargs):
            self.assertEqual(command[:4], [self.module.RUN, '/usr/bin/env',
                                          'DISPLAY=:3', '/usr/bin/xinput'])
            self.assertEqual(kwargs['timeout'], 8)
            tail = command[4:]
            calls.append(tail)
            if tail == ['--list', '--short']:
                return 'xwayland-touch:14 id=7 [slave pointer (2)]\n'
            if tail == ['--list', '--long', '7']:
                return 'Abs MT Position X\nAbs MT Position Y\nTouch mode: direct\n'
            if tail == ['list-props', '7']:
                return f'Device Enabled (123): {0 if disabled else 1}\n'
            if tail == ['disable', '7'] and fail_disable:
                raise subprocess.TimeoutExpired(command, 8)
            if tail not in (['disable', '7'], ['enable', '7']):
                self.fail(f'Unexpected command: {tail}')
            return ''

        with patch.object(self.module.os, 'getuid', return_value=0), \
             patch.object(self.module.sys, 'argv', ['reset_nested_touch.py', *args]), \
             patch.object(self.module.Path, 'read_text',
                          return_value='SM-T630-T630XXSBDZE3-Ubuntu-v1'), \
             patch.object(self.module, 'physical_contacts', return_value=contacts), \
             patch.object(self.module.subprocess, 'check_output', side_effect=xinput), \
             patch('builtins.print'):
            try:
                self.module.main()
            except BaseException as exc:
                return calls, exc
        return calls, None

    def test_default_is_read_only(self):
        calls, error = self.run_reset()
        self.assertIsNone(error)
        self.assertFalse(any(call[0] in ('disable', 'enable') for call in calls))

    def test_only_private_virtual_touch_is_reset(self):
        calls, error = self.run_reset(['--reset'])
        self.assertIsNone(error)
        self.assertEqual([call for call in calls if call[0] in ('disable', 'enable')],
                         [['disable', '7'], ['enable', '7']])

    def test_active_contact_refuses_without_change(self):
        calls, error = self.run_reset(['--reset'], contacts=1)
        self.assertIsInstance(error, SystemExit)
        self.assertFalse(any(call[0] in ('disable', 'enable') for call in calls))

    def test_disabled_device_is_not_assumed_safe_to_reset(self):
        calls, error = self.run_reset(['--reset'], disabled=True)
        self.assertIsInstance(error, SystemExit)
        self.assertFalse(any(call[0] in ('disable', 'enable') for call in calls))

    def test_disable_timeout_still_attempts_reenable(self):
        calls, error = self.run_reset(['--reset'], fail_disable=True)
        self.assertIsInstance(error, subprocess.TimeoutExpired)
        self.assertEqual(calls[-1], ['enable', '7'])

    def test_ambiguous_or_missing_virtual_touch_refused(self):
        for value in ('', 'xwayland-pointer:14 id=7',
                      'xwayland-touch:14 id=7\nxwayland-touch:15 id=8'):
            with self.assertRaises(ValueError):
                self.module.virtual_touch(value)


if __name__ == '__main__':
    unittest.main()
