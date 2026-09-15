import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('pressure_observer',
    Path(__file__).with_name('observe_pen_pressure.py'))
pressure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pressure)


class PenPressureObserverTests(unittest.TestCase):
    def test_queries_only_pressure_axis_and_validates_range(self):
        def ioctl(fd, request, target):
            self.assertEqual(fd, 17)
            self.assertEqual(request & 255, 0x40 + 0x18)
            self.assertEqual(len(target), 24)
            target[:] = struct.pack('@6i', 123, 0, 4095, 0, 0, 0)
        with patch.object(pressure.fcntl, 'ioctl', side_effect=ioctl):
            self.assertEqual(pressure.read_pressure(17), (123, 4095))

    def test_invalid_pressure_state_refused(self):
        for value, minimum, maximum in ((-1, 0, 4095), (4096, 0, 4095),
                                         (1, 1, 4095), (0, 0, 0), (0, 0, 65536)):
            def ioctl(_fd, _request, target):
                target[:] = struct.pack('@6i', value, minimum, maximum, 0, 0, 0)
            with patch.object(pressure.fcntl, 'ioctl', side_effect=ioctl):
                with self.assertRaises(ValueError):
                    pressure.read_pressure(17)

    def test_unknown_device_or_unbounded_duration_never_opens_input(self):
        with patch.object(pressure.os, 'getuid', return_value=0), \
             patch.object(pressure.Path, 'read_text', return_value='unknown'), \
             patch.object(pressure.os, 'open') as open_input:
            for seconds in (0, 121, 30):
                with self.assertRaises(ValueError):
                    pressure.observe(seconds)
            open_input.assert_not_called()

    def test_descriptor_closed_when_axis_query_fails(self):
        with patch.object(pressure.os, 'getuid', return_value=0), \
             patch.object(pressure.Path, 'read_text', side_effect=[
                 'SM-T630-T630XXSBDZE3-Ubuntu-v1', 'sec_e-pen']), \
             patch.object(pressure.os, 'open', return_value=17), \
             patch.object(pressure, 'read_pressure', side_effect=OSError), \
             patch.object(pressure.os, 'close') as close_input:
            with self.assertRaises(OSError):
                pressure.observe(15)
            close_input.assert_called_once_with(17)


if __name__ == '__main__':
    unittest.main()
