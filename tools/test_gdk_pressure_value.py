import unittest
from gdk_pressure_value import pressure_value


class GdkPressureValueTests(unittest.TestCase):
    def test_nullable_double_including_zero(self):
        for value in (0.0, 0.25, 1.0):
            self.assertEqual(pressure_value(value), value)
        self.assertIsNone(pressure_value(None))

    def test_legacy_pair(self):
        self.assertEqual(pressure_value((True, 0.5)), 0.5)
        self.assertEqual(pressure_value((True, 0.0)), 0.0)
        self.assertIsNone(pressure_value((False, 0.0)))

    def test_invalid_values_do_not_enter_summary(self):
        for value in (True, False, -0.1, 1.1, float('nan'), float('inf'),
                      '0.5', (), (True,), (True, 0.1, 0.2), (1, 0.5)):
            self.assertIsNone(pressure_value(value))
