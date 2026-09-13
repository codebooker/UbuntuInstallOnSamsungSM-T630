#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class RuntimeHealthTests(unittest.TestCase):
    def test_wifi_check_discovers_connected_interface_without_ssid(self):
        source = ROOT / 'tools/check_runtime_health.sh'
        subprocess.run(['sh', '-n', source], check=True)
        text = source.read_text()
        self.assertIn('DEVICE,TYPE,STATE', text)
        self.assertIn('$3 == "connected"', text)
        self.assertNotIn('GENERAL.CONNECTION', text)
        self.assertNotIn('device show wlan0', text)

    def test_bluetooth_health_includes_audio_profile_registration(self):
        text = (ROOT / 'tools/check_runtime_health.sh').read_text()
        self.assertIn('/UUID: Audio Source/', text)
        self.assertIn('/UUID: Audio Sink/', text)
        self.assertIn('audio_source=', text)
        self.assertIn('audio_sink=', text)

    def test_shared_device_permissions_are_observed_not_repaired(self):
        text = (ROOT / 'tools/check_runtime_health.sh').read_text()
        self.assertIn("stat -c '%U:%G:%a' /dev/fuse", text)
        self.assertIn("stat -c '%U:%G:%a' /dev/video32", text)
        self.assertIn('device_permissions:', text)
        self.assertNotIn('chmod ', text)
        self.assertNotIn('chown ', text)

    def test_health_output_does_not_emit_controller_or_network_identifiers(self):
        text = (ROOT / 'tools/check_runtime_health.sh').read_text()
        self.assertNotIn('GENERAL.CONNECTION', text)
        self.assertNotIn('GENERAL.HWADDR', text)
        self.assertNotIn('Address:', text)

    def test_desktop_battery_uses_upower_display_device(self):
        text = (ROOT / 'tools/check_runtime_health.sh').read_text()
        self.assertIn('/org/freedesktop/UPower/devices/DisplayDevice', text)
        self.assertIn('desktop_battery:', text)


if __name__ == '__main__':
    unittest.main()
