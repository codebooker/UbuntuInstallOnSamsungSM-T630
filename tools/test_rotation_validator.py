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
        self.assertIn("len(orientations) >= 2 and len(transforms) >= 2", source)
        self.assertNotIn('/dev/input', source)
        self.assertNotIn('ScreenSaver.SetActive', source)


if __name__ == '__main__':
    unittest.main()
