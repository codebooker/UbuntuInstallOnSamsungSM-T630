#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest


source = Path(__file__).with_name("assemble_waydroid_module_payload.py")
spec = importlib.util.spec_from_file_location("assemble_waydroid_modules", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
closure = module.load_sibling("audit_waydroid_module_closure.py")


class AssembleWaydroidModulesTests(unittest.TestCase):
    def test_selection_uses_external_wlan_and_omits_only_known_modules(self):
        selected = {
            "touch.ko": Path("stock/touch.ko"),
            "qca_cld3_wlan.ko": Path("stock/qca_cld3_wlan.ko"),
            **{name: Path("stock") / name
               for name in closure.PERMITTED_UNUSED_MODULES},
        }
        built = {
            "touch.ko": Path("build/touch.ko"),
            "tas256x_dlkm.ko": Path("build/tas256x_dlkm.ko"),
        }
        wlan = Path("external/qca_cld3_wlan.ko")
        chosen, omitted = module.choose_modules(selected, built, wlan, closure)
        self.assertEqual(chosen, {
            "touch.ko": Path("build/touch.ko"),
            "qca_cld3_wlan.ko": wlan,
        })
        self.assertEqual(omitted, closure.PERMITTED_UNUSED_MODULES)

    def test_unknown_module_gap_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "camera.ko"):
            module.choose_modules(
                {"camera.ko": Path("stock/camera.ko")}, {},
                Path("external/qca_cld3_wlan.ko"), closure,
            )

    def test_module_list_is_filtered(self):
        chosen = {"audio.ko", "codec.ko"}
        self.assertEqual(
            module.filtered_module_list("audio.ko\nrmnet.ko\ncodec.ko\n", chosen),
            "audio.ko\ncodec.ko\n",
        )

    def test_dependency_file_is_generated_from_new_modules(self):
        records = [
            {"file": "audio.ko", "internal_name": "audio",
             "depends": "codec,tas"},
            {"file": "codec.ko", "internal_name": "codec", "depends": ""},
            {"file": "tas.ko", "internal_name": "tas", "depends": "codec"},
        ]
        self.assertEqual(
            module.generated_modules_dep(records),
            "/vendor/lib/modules/audio.ko: /vendor/lib/modules/codec.ko "
            "/vendor/lib/modules/tas.ko\n"
            "/vendor/lib/modules/codec.ko:\n"
            "/vendor/lib/modules/tas.ko: /vendor/lib/modules/codec.ko\n",
        )

    def test_dependency_on_unavailable_module_fails(self):
        with self.assertRaisesRegex(ValueError, "unavailable dependency"):
            closure.expand_dependency_filenames(
                {"audio.ko"}, {"audio.ko": "audio"},
                {"audio": {"missing"}},
            )

    def test_project_profile_accepts_gtact4pro_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            build = Path(temporary)
            command = build / "techpack/audio/asoc/.lahaina.o.cmd"
            command.parent.mkdir(parents=True)
            command.write_text(
                "-include /src/tree/techpack/audio/config/"
                "lahaina_gtact4pro.h\n"
            )
            self.assertEqual(module.verify_project_profile(build), command)

    def test_project_profile_rejects_other_samsung_product(self):
        with tempfile.TemporaryDirectory() as temporary:
            build = Path(temporary)
            command = build / "techpack/audio/asoc/.lahaina.o.cmd"
            command.parent.mkdir(parents=True)
            command.write_text(
                "-include /src/tree/techpack/audio/config/lahaina_a52s.h\n"
            )
            with self.assertRaisesRegex(ValueError, "PROJECT_NAME=gtact4prowifi"):
                module.verify_project_profile(build)


if __name__ == "__main__":
    unittest.main()
