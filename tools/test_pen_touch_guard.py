import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1] / 'ubuntu/t630-pen-touch-guard.py'
SPEC = importlib.util.spec_from_file_location('pen_touch_guard', SOURCE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class PenTouchGuardTests(unittest.TestCase):
    def test_key_bitmap_tracks_pen_and_eraser_proximity(self):
        keys = bytearray(guard.KEY_BYTES)
        self.assertFalse(guard._pressed(keys, guard.BTN_TOOL_PEN))
        keys[guard.BTN_TOOL_PEN // 8] |= 1 << (guard.BTN_TOOL_PEN % 8)
        self.assertTrue(guard._pressed(keys, guard.BTN_TOOL_PEN))
        self.assertFalse(guard._pressed(keys, guard.BTN_TOOL_RUBBER))

    def test_ioctl_reads_only_current_tool_key_state(self):
        def ioctl(_fd, request, keys, mutate):
            self.assertEqual(request, guard._eviocgkey(guard.KEY_BYTES))
            self.assertTrue(mutate)
            keys[guard.BTN_TOOL_RUBBER // 8] |= 1 << (guard.BTN_TOOL_RUBBER % 8)
        with patch.object(guard.fcntl, 'ioctl', side_effect=ioctl):
            self.assertTrue(guard.tool_in_proximity(12))

    def test_touch_transition_is_verified_and_idempotent(self):
        path = SimpleNamespace(read_text=Mock(side_effect=['1', '0', '0', '0']),
                               write_text=Mock())
        with patch.object(guard, 'TOUCH_ENABLED', path):
            guard.set_touch_enabled(False)
            guard.set_touch_enabled(False)
        path.write_text.assert_called_once_with('0')

    def test_installer_starts_guard_without_input_grab(self):
        source = SOURCE.read_text()
        self.assertNotIn('EVIOCGRAB', source)
        self.assertNotIn('/dev/input/event5', source)
        self.assertIn("PEN_EVENT = Path('/dev/input/event7')", source)
        startup = SOURCE.with_name('t630-desktop-autostart').read_text()
        self.assertIn('pgrep -x t630-pen-guard', startup)
        self.assertIn('/usr/local/sbin/t630-pen-touch-guard', startup)


if __name__ == '__main__':
    unittest.main()
