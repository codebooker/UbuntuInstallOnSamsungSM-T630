#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools/check_waydroid_gapps.py"
SPEC = importlib.util.spec_from_file_location("check_waydroid_gapps", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WaydroidGappsTests(unittest.TestCase):
    def test_status_parser_ignores_network_identifiers(self):
        status = MODULE.parse_status(
            "Session:\tRUNNING\nContainer:\tRUNNING\nIP address:\t192.0.2.1\n"
        )
        self.assertEqual(status["session"], "RUNNING")
        self.assertEqual(status["container"], "RUNNING")

    def test_frozen_is_a_normal_idle_container_state(self):
        status = MODULE.parse_status("Session: RUNNING\nContainer: FROZEN\n")
        self.assertEqual(status["session"], "RUNNING")
        self.assertIn(status["container"], ("RUNNING", "FROZEN"))

    def test_only_official_arm64_gapps_channel_is_accepted(self):
        valid = {
            "arch": "arm64",
            "vendor_type": "MAINLINE",
            "system_ota": MODULE.GAPPS_OTA,
            "vendor_ota": MODULE.VENDOR_OTA,
        }
        self.assertTrue(MODULE.is_gapps_config(valid))
        invalid = dict(valid, system_ota=valid["system_ota"].replace("GAPPS", "VANILLA"))
        self.assertFalse(MODULE.is_gapps_config(invalid))

    def test_config_reader_uses_waydroid_section(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "waydroid.cfg"
            path.write_text(
                "[waydroid]\narch = arm64\nvendor_type = MAINLINE\n"
                f"system_ota = {MODULE.GAPPS_OTA}\n"
                f"vendor_ota = {MODULE.VENDOR_OTA}\n",
                encoding="utf-8",
            )
            self.assertTrue(MODULE.is_gapps_config(MODULE.read_waydroid_config(path)))

    def test_identifier_is_never_printed(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("value suppressed", source)
        self.assertNotIn("print(identifier", source)
        self.assertNotIn("print(result.stdout", source)

    def test_accepted_image_digests_are_pinned(self):
        self.assertEqual(set(MODULE.ACCEPTED_IMAGE_SHA256), {"system.img", "vendor.img"})
        for digest in MODULE.ACCEPTED_IMAGE_SHA256.values():
            self.assertEqual(len(digest), 64)
            int(digest, 16)


if __name__ == "__main__":
    unittest.main()
