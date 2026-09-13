#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ubuntu/test-t630-camera-frame.py"
SPEC = importlib.util.spec_from_file_location("camera_frame", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CameraFrameValidationTests(unittest.TestCase):
    def test_luma_statistics(self):
        pixels = bytes([0, 10, 20, 255]) * (MODULE.WIDTH * MODULE.HEIGHT // 4)
        result = MODULE.summarize_luma(pixels)
        self.assertEqual(result["minimum"], 0)
        self.assertEqual(result["maximum"], 255)
        self.assertEqual(result["median"], 20)
        self.assertEqual(result["mean"], 71.25)
        self.assertEqual(result["near_black_fraction"], 0.25)
        self.assertEqual(result["near_white_fraction"], 0.25)

    def test_capture_is_volatile_and_exactly_scoped(self):
        text = SOURCE.read_text()
        self.assertIn('choices=("front", "rear")', text)
        self.assertIn('/run/user/1000', text)
        self.assertIn('path.unlink(missing_ok=True)', text)
        self.assertIn('["sudo", "-n", CONTROL, "disable"]', text)
        self.assertNotIn("/data/", text)


if __name__ == "__main__":
    unittest.main()
