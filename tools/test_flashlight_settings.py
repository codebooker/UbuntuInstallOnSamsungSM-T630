#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630_display.py'
spec = importlib.util.spec_from_file_location('display_flashlight', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FlashlightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.torch = root / 'led:torch_0'
        self.switch = root / 'led:switch_0'
        self.torch.mkdir()
        self.switch.mkdir()
        for node, maximum in ((self.torch, 500), (self.switch, 255)):
            (node / 'max_brightness').write_text(str(maximum))
            (node / 'brightness').write_text('99')
        self.light = module.FlashlightSettings(self.torch, self.switch)

    def test_startup_and_off_clear_both_nodes(self):
        self.assertEqual((self.torch / 'brightness').read_text(), '0')
        self.assertEqual((self.switch / 'brightness').read_text(), '0')
        self.light.on()
        self.light.off()
        self.assertEqual((self.torch / 'brightness').read_text(), '0')
        self.assertEqual((self.switch / 'brightness').read_text(), '0')

    def test_on_uses_safe_current_then_switch(self):
        self.light.set_brightness(100)
        self.light.on()
        self.assertEqual((self.torch / 'brightness').read_text(), '300')
        self.assertEqual((self.switch / 'brightness').read_text(), '1')
        self.assertTrue(self.light.status()['enabled'])

    def test_lease_expiry_fails_off(self):
        with mock.patch.object(module.time, 'monotonic', side_effect=[10, 24, 25]):
            self.light.on()
            self.light.expire()
            self.assertTrue(self.light.enabled)
            self.light.expire()
            self.assertFalse(self.light.enabled)
        self.assertEqual((self.torch / 'brightness').read_text(), '0')
        self.assertEqual((self.switch / 'brightness').read_text(), '0')

    def test_brightness_is_bounded(self):
        for value in (-1, 0, 4, 101, 1000, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.light.set_brightness(value)

    def test_wrong_nodes_are_rejected(self):
        (self.torch / 'max_brightness').write_text('1000')
        with self.assertRaises(ValueError):
            module.FlashlightSettings(self.torch, self.switch)


if __name__ == '__main__':
    unittest.main()
