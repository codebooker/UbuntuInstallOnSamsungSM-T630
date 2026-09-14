#!/usr/bin/env python3

from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_t630_sensor_stack.sh"


class SensorStackBuilderTests(unittest.TestCase):
    def setUp(self):
        self.source = BUILDER.read_text(encoding="utf-8")

    def test_shell_is_valid_and_sources_are_pinned(self):
        subprocess.run(["sh", "-n", BUILDER], check=True)
        self.assertIn("bb55ceb87b61db7629c0820101ce7884ff8d987b", self.source)
        self.assertEqual(len(re.findall(r"(?m)^  [0-9a-f]{64} \\$", self.source)), 4)
        self.assertIn("Source archive checksum mismatch", self.source)
        self.assertIn("meson==1.7.2", self.source)
        self.assertIn("82c6818dc81743c96de3a458f06175776ebfde4081195ea31ea6971838f25e38",
                      self.source)
        self.assertIn("--require-hashes", self.source)
        self.assertNotIn("git clone", self.source)
        self.assertNotIn("/work/reference-s9-ultra", self.source)

    def test_device_patches_and_package_versions_are_explicit(self):
        for patch in (
            "use-t630-auto-brightness.patch",
            "hexagonrpcd-downstream-fastrpc.patch",
            "iio-sensor-proxy-downstream-fastrpc-subsystem.patch",
        ):
            self.assertIn(f'$repo/patches/{patch}', self.source)
            self.assertTrue((ROOT / "patches" / patch).is_file())
        self.assertIn("libssc 0.4.4-t6303", self.source)
        self.assertIn("hexagonrpcd 0.4.0-t6303", self.source)
        self.assertIn("iio-sensor-proxy 3.9-t6303", self.source)
        self.assertIn('git apply --recount "$repo/patches/hexagonrpcd-downstream-fastrpc.patch"',
                      self.source)
        self.assertIn("T630_SKIP_BUILD_DEPS", self.source)
        self.assertIn("T630_SENSOR_BUILD_ROOT", self.source)
        self.assertIn("libssc|hexagonrpcd", self.source)
        self.assertIn("DEBIAN/postinst", self.source)
        self.assertIn("'ldconfig'", self.source)


if __name__ == "__main__":
    unittest.main()
