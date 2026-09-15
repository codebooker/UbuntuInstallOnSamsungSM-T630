#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630_display.py'
spec = importlib.util.spec_from_file_location('display', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DisplayTests(unittest.TestCase):
    def test_missing_state_directory_is_created_privately(self):
        prefs = self.root / 'new-state' / 'settings.json'
        settings = module.DisplaySettings(self.root, self.off, prefs)
        settings.request('BRIGHTNESS 40')
        self.assertTrue(settings.flush(force=True))
        self.assertEqual(prefs.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(prefs.stat().st_mode & 0o777, 0o600)
        self.assertEqual(module.DisplaySettings(self.root, self.off, prefs).status()['brightness'], 40)

    def test_save_failure_does_not_disable_controls_and_can_retry(self):
        self.settings.request('BRIGHTNESS 40')
        with patch.object(module.os, 'open', side_effect=PermissionError('test')):
            self.assertFalse(self.settings.flush(force=True))
        self.assertIsNotNone(self.settings.dirty_at)
        self.settings.request('BRIGHTNESS 65')
        self.assertEqual(self.settings.status()['brightness'], 65)
        self.assertTrue(self.settings.flush(force=True))

    def test_symlinked_state_directory_is_refused_without_killing_controls(self):
        target = self.root / 'target'
        target.mkdir()
        link = self.root / 'linked-state'
        link.symlink_to(target, target_is_directory=True)
        settings = module.DisplaySettings(self.root, self.off, link / 'settings.json')
        settings.request('BRIGHTNESS 40')
        self.assertFalse(settings.flush(force=True))
        self.assertFalse((target / 'settings.json').exists())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'max_brightness').write_text('306')
        (self.root / 'brightness').write_text('255')
        self.off = self.root / 'off'
        self.prefs = self.root / 'settings.json'
        self.settings = module.DisplaySettings(self.root, self.off, self.prefs)

    def test_brightness_does_not_wake_locked_panel(self):
        self.off.write_text('255')
        (self.root / 'brightness').write_text('0')
        self.settings.request('BRIGHTNESS 50')
        self.assertEqual((self.root / 'brightness').read_text(), '0')
        self.assertEqual(self.off.read_text(), '153')

    def test_preferences_survive_start(self):
        self.settings.request('BRIGHTNESS 35')
        self.settings.request('IDLE 600')
        self.settings.request('AUTO_SUSPEND ON')
        self.settings.flush(force=True)
        new = module.DisplaySettings(self.root, self.off, self.prefs)
        self.assertEqual(new.status()['brightness'], 35)
        self.assertEqual(new.idle_seconds, 600)
        self.assertTrue(new.auto_suspend)

    def test_rejects_unbounded_requests(self):
        for text in ('BRIGHTNESS 0', 'BRIGHTNESS 101', 'BRIGHTNESS -1',
                     'BRIGHTNESS nan', 'IDLE 1', 'IDLE 999999', 'UNLOCK',
                     'SHUTDOWN', 'BRIGHTNESS 50 extra'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.settings.request(text)

    def test_automatic_suspend_is_explicit_and_bounded(self):
        self.assertFalse(self.settings.status()['auto_suspend'])
        self.settings.request('AUTO_SUSPEND ON')
        self.assertTrue(self.settings.status()['auto_suspend'])
        self.settings.request('AUTO_SUSPEND OFF')
        self.assertFalse(self.settings.status()['auto_suspend'])
        for text in ('AUTO_SUSPEND TRUE', 'AUTO_SUSPEND 1', 'AUTO_SUSPEND ON EXTRA'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.settings.request(text)

    def test_old_preferences_default_to_manual_suspend(self):
        self.prefs.write_text('{"brightness": 40, "idle_seconds": 300}')
        new = module.DisplaySettings(self.root, self.off, self.prefs)
        self.assertFalse(new.auto_suspend)

    def test_transient_flashlight_state_is_not_persisted(self):
        self.settings.request('BRIGHTNESS 45')
        self.settings.flush(force=True)
        saved = self.prefs.read_text()
        self.assertNotIn('flashlight', saved)
        self.assertNotIn('blanked', saved)

    def test_keep_awake_and_temporary_inhibit(self):
        self.settings.request('IDLE 0')
        self.assertEqual(self.settings.idle_seconds, 0)
        self.settings.request('INHIBIT')
        self.assertGreater(self.settings.inhibit_until, module.time.monotonic())
        self.assertFalse(self.off.exists())

    def test_system_actions_are_exact_and_one_shot(self):
        self.settings.request('SYSTEM REBOOT')
        with self.assertRaises(ValueError):
            self.settings.request('SYSTEM POWEROFF')
        self.assertEqual(self.settings.take_system_action(), 'reboot')
        self.assertIsNone(self.settings.take_system_action())
        self.settings.request('SYSTEM POWEROFF')
        self.assertEqual(self.settings.take_system_action(), 'poweroff')
        for request in ('SYSTEM OFF', 'SYSTEM RESTART', 'SYSTEM POWEROFF NOW'):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.settings.request(request)

    def test_refuses_other_backlight(self):
        (self.root / 'max_brightness').write_text('0')
        with self.assertRaises(ValueError):
            module.DisplaySettings(self.root, self.off, self.prefs)

    def test_invalid_preferences_do_not_disable_power_monitor(self):
        self.prefs.write_text('{broken')
        new = module.DisplaySettings(self.root, self.off, self.prefs)
        self.assertEqual(new.idle_seconds, 300)
        self.assertEqual((self.root / 'brightness').read_text(), '255')


if __name__ == '__main__':
    unittest.main()
