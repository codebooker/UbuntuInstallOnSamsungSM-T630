#!/usr/bin/env python3
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'ubuntu' / '51-t630-bluetooth.lua'


class WirePlumberBluetoothConfigTests(unittest.TestCase):
    def test_bluez_audio_is_enabled(self):
        text = CONFIG.read_text()
        self.assertIn('bluez_monitor.enabled = true', text)
        self.assertNotIn('bluez_monitor.enabled = false', text)

    def test_unvalidated_midi_is_disabled(self):
        text = CONFIG.read_text()
        self.assertIn('bluez_midi_monitor.enabled = false', text)

    def test_obsolete_override_is_gone(self):
        self.assertFalse((ROOT / 'ubuntu' / '51-t630-no-bluetooth.lua').exists())


if __name__ == '__main__':
    unittest.main()
