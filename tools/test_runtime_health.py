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


if __name__ == '__main__':
    unittest.main()
