#!/usr/bin/env python3
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest import mock
from contextlib import ExitStack
import tempfile
import types
import subprocess
import sys

local = Path(__file__).resolve().parents[1] / 'ubuntu/t630-suspend.py'
source = local if local.exists() else Path('/usr/local/sbin/t630-suspend')
loader = importlib.machinery.SourceFileLoader('tablet_suspend', str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules['tablet_suspend'] = module
loader.exec_module(module)


class Guards(unittest.TestCase):
    def test_ready_only_on_battery(self):
        self.assertTrue(module.can_suspend('Discharging', ['not attached'], 'ONLINE', True, True, False))

    def test_charger_blocks(self):
        self.assertFalse(module.can_suspend('Charging', ['not attached'], 'ONLINE', True, True, False))

    def test_usb_blocks_even_if_battery_discharging(self):
        self.assertFalse(module.can_suspend('Discharging', ['configured'], 'ONLINE', True, True, False))

    def test_missing_usb_state_blocks(self):
        self.assertFalse(module.can_suspend('Discharging', [], 'ONLINE', True, True, False))

    def test_ipa_not_ready_blocks(self):
        self.assertFalse(module.can_suspend('Discharging', ['not attached'], 'OFFLINING', True, True, False))

    def test_unlocked_or_lit_blocks(self):
        for lock, blank in ((False, True), (True, False)):
            self.assertFalse(module.can_suspend('Discharging', ['not attached'], 'ONLINE', lock, blank, False))

    def test_playing_audio_blocks(self):
        self.assertFalse(module.can_suspend('Discharging', ['not attached'], 'ONLINE', True, True, True))

    def test_active_vendor_wifi_can_have_a_predictable_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / 'wlp1s0'
            inactive = root / 'swlan0'
            for interface, carrier, address in (
                    (active, '1', '02:00:00:00:00:01'),
                    (inactive, '0', '02:00:00:00:00:02')):
                interface.mkdir()
                for name, value in (('carrier', carrier), ('address', address),
                                    ('wowl_add_ptrn', ''), ('wowl_del_ptrn', '')):
                    (interface / name).write_text(value)
            self.assertEqual(module.wifi_interface(root).name, 'wlp1s0')

    def test_ambiguous_connected_vendor_wifi_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('wlan0', 'wlan1'):
                interface = root / name
                interface.mkdir()
                for attribute, value in (('carrier', '1'),
                                         ('address', '02:00:00:00:00:01'),
                                         ('wowl_add_ptrn', ''), ('wowl_del_ptrn', '')):
                    (interface / attribute).write_text(value)
            with self.assertRaises(RuntimeError):
                module.wifi_interface(root)


class HelperCleanup(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        files = {
            '/etc/t630-install-id': 'SM-T630-T630XXSBDZE3-Ubuntu-v1',
            '/etc/t630/suspend.enabled': '',
            '/sys/module/lpm_levels/parameters/sleep_disabled': 'Y',
            '/sys/power/state': 'freeze mem',
            '/sys/class/rtc/rtc0/device/power/wakeup': 'enabled',
            '/sys/class/net/wlan0/address': '02:00:00:00:00:01',
            '/sys/class/net/wlan0/carrier': '1',
            '/sys/class/net/wlan0/wowl_add_ptrn': '',
            '/sys/class/net/wlan0/wowl_del_ptrn': '',
            '/sys/class/power_supply/battery/status': 'Discharging',
            '/sys/class/udc/test/state': 'not attached',
            '/sys/bus/platform/devices/soc:qcom,ipa_fws/subsys0/state': 'ONLINE',
            '/run/t630-display-off-brightness': '254',
            '/sys/class/backlight/panel0-backlight/brightness': '0',
            '/sys/class/rtc/rtc0/wakealarm': '',
            '/sys/kernel/wakeup_reasons/last_resume_reason': '216 pm8xxx_rtc_alarm',
        }
        for name, value in files.items():
            path = self.path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        self.patch('Path', side_effect=self.path)
        self.patch('os.geteuid', return_value=0)
        self.patch('os.uname', return_value=types.SimpleNamespace(
            release='5.4.274-qgki-31225846-abT630XXSBDZE3'))
        self.patch('sys.argv', ['t630-suspend'])
        self.patch('command', side_effect=['(true,)', '(<true>,)', '[]'])
        self.patch('open', mock.mock_open(), create=True)
        self.patch('fcntl.flock')
        self.patch('os.sync')
        self.patch('time.sleep')
        self.patch('time.CLOCK_BOOTTIME', 7, create=True)
        self.patch('time.clock_gettime', side_effect=[100, 116])
        self.patch('time.monotonic', side_effect=[50, 51])
        self.sensors_active = self.patch('sensor_bridge_active', return_value=False)
        self.stop_sensors = self.patch('stop_sensor_bridge')
        self.start_sensors = self.patch('start_sensor_bridge')
        self.run = self.patch('subprocess.run', return_value=types.SimpleNamespace(returncode=0))

    def path(self, name):
        return self.root / str(name).lstrip('/')

    def patch(self, name, *args, **kwargs):
        return self.stack.enter_context(mock.patch('tablet_suspend.' + name, *args, **kwargs))

    def cleaned(self):
        self.assertEqual(self.path('/sys/class/net/wlan0/wowl_del_ptrn').read_text(), module.PATTERN)
        self.assertEqual(self.run.call_args_list[-1].args[0][1:3], ['-m', 'disable'])

    def test_timer_wake_does_not_request_display_wake(self):
        result = module.main()
        self.assertTrue(result['slept'])
        self.assertFalse(result['power_wake'])
        self.assertEqual(result['seconds'], 15)
        self.cleaned()

    def test_physical_power_reason_is_identified(self):
        self.path('/sys/kernel/wakeup_reasons/last_resume_reason').write_text('212 pon_kpdpwr_status')
        self.assertTrue(module.main()['power_wake'])
        self.cleaned()

    def test_active_sensor_bridge_is_stopped_and_restarted(self):
        self.sensors_active.return_value = True
        self.assertTrue(module.main()['slept'])
        self.stop_sensors.assert_called_once_with()
        self.start_sensors.assert_called_once_with()
        self.cleaned()

    def test_failed_suspend_still_cleans_up(self):
        self.run.return_value.returncode = 1
        self.assertFalse(module.main()['slept'])
        self.cleaned()

    def test_timeout_still_cleans_up(self):
        self.run.side_effect = [subprocess.TimeoutExpired('rtcwake', 330),
                                types.SimpleNamespace(returncode=0)]
        with self.assertRaises(subprocess.TimeoutExpired):
            module.main()
        self.cleaned()

    def test_alarm_cleanup_failure_still_removes_wifi_pattern(self):
        self.run.side_effect = [types.SimpleNamespace(returncode=0),
                                subprocess.TimeoutExpired('rtcwake', 5)]
        with self.assertRaises(subprocess.TimeoutExpired):
            module.main()
        self.cleaned()


if __name__ == '__main__':
    unittest.main()
