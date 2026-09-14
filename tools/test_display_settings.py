#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630_display.py'
spec = importlib.util.spec_from_file_location('display', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DisplayTests(unittest.TestCase):
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
