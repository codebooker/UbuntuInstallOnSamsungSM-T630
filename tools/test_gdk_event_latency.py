import unittest
from gdk_event_latency import event_age_ms


class GdkEventLatencyTests(unittest.TestCase):
    def test_normal_age_and_32_bit_wrap(self):
        self.assertEqual(event_age_ms(1000, 1015), 15)
        self.assertEqual(event_age_ms(2**32 - 5, 2**32 + 7), 12)
        self.assertEqual(event_age_ms(100, 100), 0)

    def test_unknown_stale_and_incompatible_clocks_are_rejected(self):
        for timestamp, now in ((0, 10), (True, 10), (-1, 10), (2**32, 10),
                               (10, True), (10, 9), (10, 30011), (10, -1),
                               (10, float('nan')), (10, float('inf'))):
            self.assertIsNone(event_age_ms(timestamp, now))
