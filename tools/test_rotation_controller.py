#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RotationControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "ubuntu/t630-rotation-controller.py"
        spec = importlib.util.spec_from_file_location("t630_rotation", path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_sm_t630_landscape_sensor_correction(self):
        self.assertEqual(self.module.mapped_transform("left-up"), 1)
        self.assertEqual(self.module.mapped_transform("bottom-up"), 2)
        self.assertEqual(self.module.mapped_transform("right-up"), 3)
        self.assertEqual(self.module.mapped_transform("normal"), 0)
        self.assertEqual(self.module.TRANSFORM_MODES[1], (1920, 1200))
        self.assertEqual(self.module.TRANSFORM_MODES[2], (1200, 1920))

    def test_flat_or_unknown_readings_are_ignored(self):
        self.assertIsNone(self.module.mapped_transform("undefined"))
        self.assertIsNone(self.module.mapped_transform("unexpected"))

    def test_lock_cancels_queued_rotation_and_unlock_settles_again(self):
        state = {'pending': 'bottom-up', 'since': 10.0}
        self.module.queue_rotation(state, 'bottom-up', True, 11.0)
        self.assertIsNone(state['pending'])
        self.module.queue_rotation(state, 'bottom-up', False, 20.0)
        self.assertEqual(state, {'pending': 'bottom-up', 'since': 20.0})
        self.module.queue_rotation(state, 'bottom-up', False, 20.5)
        self.assertEqual(state['since'], 20.0)

    def test_lock_ignores_all_physical_orientations(self):
        for orientation in self.module.ORIENTATION_TRANSFORMS:
            state = {'pending': None, 'since': 10.0}
            self.module.queue_rotation(state, orientation, True, 20.0)
            self.assertIsNone(state['pending'])

    def test_extension_and_controller_share_rotation_lock_and_hide_stock_controls(self):
        extension = (ROOT / 'ubuntu/gnome-tablet-tools/extension.js').read_text()
        controller = (ROOT / 'ubuntu/t630-rotation-controller.py').read_text()
        schema = (ROOT / 'ubuntu/gnome-tablet-tools/schemas/'
                  'org.gnome.shell.extensions.t630-tablet-tools.gschema.xml').read_text()
        self.assertIn("bind('rotation-locked'", extension)
        self.assertIn("get_boolean('rotation-locked')", controller)
        self.assertIn('<key name="rotation-locked" type="b">', schema)
        self.assertIn('_brightness?.quickSettingsItems?.[0]', extension)
        self.assertIn('_autoRotate?.quickSettingsItems?.[0]', extension)

    def test_session_locks_stock_handler_and_starts_controller(self):
        session = (ROOT / "ubuntu/t630-gnome-session").read_text()
        self.assertIn("orientation-lock true", session)
        self.assertIn("/usr/local/libexec/t630-rotation-controller", session)
        self.assertIn("rotation_pid=$!", session)
        preview = (ROOT / "ubuntu/t630-gnome-preview").read_text()
        self.assertIn("1920x1200:1200x1920", preview)

    def test_desktop_weston_loads_rotation_without_exposing_fallback_panel(self):
        config = (ROOT / "ubuntu/weston-desktop.ini").read_text()
        self.assertIn("modules=t630-rotation.so", config)
        self.assertIn("panel-position=none", config)
        recovery = (ROOT / "ubuntu/weston.ini").read_text()
        self.assertNotIn("t630-rotation.so", recovery)
        self.assertIn("panel-position=top", recovery)

    def test_module_exports_the_weston_wet_entrypoint(self):
        source = (ROOT / "ubuntu/t630-weston-rotation.c").read_text()
        self.assertIn("wet_module_init", source)
        self.assertIn("weston_output_set_transform", source)
        self.assertIn("/run/t630-weston-rotation", source)


if __name__ == "__main__":
    unittest.main()
