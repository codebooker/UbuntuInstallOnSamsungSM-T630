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
        self.assertIn('check=True', text)
        self.assertLess(text.index('CONTROL, "disable"'),
                        text.index('print(json.dumps(result'))
        self.assertNotIn("/data/", text)

    def test_camera_rescan_reapplies_desktop_permissions(self):
        mounts = (ROOT / "camera/t630-camera-mounts.sh").read_text()
        scan = mounts.index("/proc/1/root/bin/busybox mdev -s")
        repair = mounts.index("python3 /usr/local/share/t630/t630-device-permissions.py")
        self.assertGreater(repair, scan)
        self.assertNotIn("chmod 666 /dev/null", mounts)

    def test_camera_control_bounds_owned_group_teardown(self):
        control = (ROOT / "ubuntu/t630-camera-control").read_text()
        self.assertIn('while pid_matches "$file" "$marker"', control)
        self.assertIn('kill -KILL -- "-$pid"', control)
        self.assertIn('test "$attempt" -lt 16', control)


if __name__ == "__main__":
    unittest.main()
