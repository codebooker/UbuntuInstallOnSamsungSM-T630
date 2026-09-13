#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DevicePermissionTests(unittest.TestCase):
    def test_mdev_rules_cover_acceleration_nodes(self):
        rules = (ROOT / "ubuntu/mdev.conf").read_text().splitlines()
        self.assertIn("kgsl-3d0 0:994 660", rules)
        self.assertIn("ion 0:994 660", rules)
        self.assertIn("video3[23] 0:994 660", rules)
        self.assertIn("(dri/)?renderD128 0:994 660", rules)

    def test_repair_validates_render_and_live_alsa_nodes(self):
        source = (ROOT / "ubuntu/t630-device-permissions.py").read_text()
        self.assertIn("'null': (1, 3)", source)
        self.assertIn("'ptmx': (5, 2)", source)
        self.assertIn("os.chmod(node, 0o666)", source)
        self.assertIn("(226, 128)", source)
        self.assertIn("/sys/bus/platform/drivers/msm_drm", source)
        self.assertIn("Path('/sys/class/sound')", source)
        self.assertIn("assert major == 116", source)
        self.assertIn("os.chown(node, 0, 29)", source)


if __name__ == "__main__":
    unittest.main()
