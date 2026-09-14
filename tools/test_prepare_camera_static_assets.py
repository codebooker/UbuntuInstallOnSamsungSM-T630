#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).with_name("prepare_camera_static_assets.py")
SPEC = importlib.util.spec_from_file_location("prepare_camera_static_assets", SOURCE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class CameraStaticAssetTests(unittest.TestCase):
    def test_known_binary_patch_maps_are_narrow(self):
        for mapping in (module.PATCHES, module.VENDOR_PATCHES):
            for _destination, (_source, _before, _after, changes) in mapping.items():
                self.assertLessEqual(len(changes), 8)
                self.assertEqual(len({item[0] for item in changes}), len(changes))

    def test_patch_rejects_wrong_preimage_and_output(self):
        data = b"abc"
        wanted = module.sha(b"axc")
        self.assertEqual(module.patched(data, ((1, ord("b"), ord("x")),), wanted), b"axc")
        with self.assertRaisesRegex(ValueError, "preimage"):
            module.patched(data, ((1, ord("q"), ord("x")),), wanted)
        with self.assertRaisesRegex(ValueError, "output checksum"):
            module.patched(data, ((1, ord("b"), ord("x")),), "0" * 64)

    def test_all_inputs_and_outputs_are_sha256_pinned(self):
        for mapping in (module.APEXES, module.VENDOR_APEXES):
            for _destination, (_source, source_hash, output_hash) in mapping.items():
                self.assertEqual(len(source_hash), 64)
                self.assertEqual(len(output_hash), 64)
        for mapping in (module.PATCHES, module.VENDOR_PATCHES):
            for _destination, (_source, source_hash, output_hash, _changes) in mapping.items():
                self.assertEqual(len(source_hash), 64)
                self.assertEqual(len(output_hash), 64)


if __name__ == "__main__":
    unittest.main()
