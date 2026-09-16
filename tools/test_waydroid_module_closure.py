#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


source = Path(__file__).with_name("audit_waydroid_module_closure.py")
spec = importlib.util.spec_from_file_location("waydroid_module_closure", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WaydroidModuleClosureTests(unittest.TestCase):
    def test_exact_known_unused_gap_is_accepted(self):
        selected = {"touch.ko", "qca_cld3_wlan.ko"} | module.PERMITTED_UNUSED_MODULES
        covered, omitted = module.plan_closure(
            selected, {"touch.ko", "tas256x_dlkm.ko"}
        )
        self.assertEqual(covered, {"touch.ko", "qca_cld3_wlan.ko"})
        self.assertEqual(omitted, module.PERMITTED_UNUSED_MODULES)

    def test_unknown_missing_module_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "camera.ko"):
            module.plan_closure({"camera.ko"}, set())

    def test_duplicate_basename_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "same.ko"):
            module.unique_by_name([Path("a/same.ko"), Path("b/same.ko")])

    def test_proc_modules_parser_uses_first_column(self):
        self.assertEqual(
            module.parse_loaded("wlan 123 0 - Live 0x0\ncnss2 456 1 wlan, Live 0x1\n"),
            {"wlan", "cnss2"},
        )

    def test_dependency_expansion_adds_build_only_module(self):
        files = {
            "machine.ko": "machine",
            "codec.ko": "codec",
            "tas.ko": "tas",
        }
        dependencies = {
            "machine": {"codec", "tas"},
            "codec": set(),
            "tas": {"codec"},
        }
        self.assertEqual(
            module.expand_dependency_filenames(
                {"machine.ko", "codec.ko"}, files, dependencies
            ),
            {"machine.ko", "codec.ko", "tas.ko"},
        )

    def test_unavailable_dependency_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unavailable dependency"):
            module.expand_dependency_filenames(
                {"machine.ko"}, {"machine.ko": "machine"},
                {"machine": {"missing"}},
            )

    def test_hyphen_and_underscore_names_are_canonicalized(self):
        self.assertEqual(module.canonical_name("snd-soc-codec"), "snd_soc_codec")


if __name__ == "__main__":
    unittest.main()
