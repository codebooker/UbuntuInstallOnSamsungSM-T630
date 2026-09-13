#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class RotationValidatorTests(unittest.TestCase):
    def test_validator_is_bounded_and_does_not_read_input(self):
        source = (ROOT / 'ubuntu/test-t630-rotation.py').read_text()
        self.assertIn("default=120", source)
        self.assertIn("10 <= args.duration <= 180", source)
        self.assertIn("AccelerometerOrientation", source)
        self.assertIn("org.gnome.Mutter.DisplayConfig", source)
        self.assertIn("EXPECTED_TRANSFORMS", source)
        self.assertIn("EXPECTED_MODES", source)
        self.assertIn("/run/t630-weston-rotation.state", source)
        self.assertIn("item['gnome_transform'] != 0", source)
        self.assertIn("SETTLE_SECONDS = 1.5", source)
        self.assertIn("and not mismatches", source)
        self.assertNotIn('/dev/input', source)
        self.assertNotIn('ScreenSaver.SetActive', source)


if __name__ == '__main__':
    unittest.main()
