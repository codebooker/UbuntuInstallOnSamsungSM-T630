#!/usr/bin/python3
"""Guarded lab suspend. Root-only; never unlocks, reloads drivers, or changes deep PM."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PATTERN = '06:01:000000000000:3f'
RUN = '/usr/local/bin/t630-gnome-run'


def command(args, timeout=8):
    return subprocess.check_output(args, text=True, timeout=timeout,
                                   stderr=subprocess.DEVNULL).strip()


def can_suspend(status, usb_states, ipa, locked, blanked, audio_active):
    return (status == 'Discharging' and bool(usb_states)
            and all(state == 'not attached' for state in usb_states)
            and ipa == 'ONLINE' and locked and blanked and not audio_active)


def main():
    assert os.geteuid() == 0
    assert sys.argv[1:] in ([], ['--check'])
    assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
    assert os.uname().release == '5.4.274-qgki-31225846-abT630XXSBDZE3'
    if (not Path('/etc/t630/suspend.enabled').exists()
            or Path('/etc/t630/suspend.disabled').exists()):
        return {'slept': False, 'reason': 'policy disabled'}
    assert Path('/sys/module/lpm_levels/parameters/sleep_disabled').read_text().strip() == 'Y'
    assert 'freeze' in Path('/sys/power/state').read_text().split()
    assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'
    iface = Path('/sys/class/net/wlan0')
    assert len((iface / 'address').read_text().strip().split(':')) == 6
    status = Path('/sys/class/power_supply/battery/status').read_text().strip()
    usb = [p.read_text().strip() for p in Path('/sys/class/udc').glob('*/state')]
    ipa = Path('/sys/bus/platform/devices/soc:qcom,ipa_fws/subsys0/state').read_text().strip()
    if status != 'Discharging' or not usb or any(s != 'not attached' for s in usb):
        return {'slept': False, 'reason': 'external power or USB connected'}
    locked = command([RUN, 'gdbus', 'call', '--session', '--dest', 'org.gnome.ScreenSaver',
                      '--object-path', '/org/gnome/ScreenSaver', '--method',
                      'org.gnome.ScreenSaver.GetActive']) == '(true,)'
    hint = command([RUN, 'gdbus', 'call', '--system', '--dest', 'org.freedesktop.login1',
                    '--object-path', '/org/freedesktop/login1/session/self', '--method',
                    'org.freedesktop.DBus.Properties.Get', 'org.freedesktop.login1.Session',
                    'LockedHint']) == '(<true>,)'
    streams = json.loads(command([RUN, 'pactl', '-f', 'json', 'list', 'sink-inputs']))
    assert isinstance(streams, list)
    assert all(isinstance(stream, dict) and isinstance(stream.get('corked'), bool)
               for stream in streams)
    blanked = (Path('/run/t630-display-off-brightness').exists()
               and Path('/sys/class/backlight/panel0-backlight/brightness').read_text().strip() == '0')
    if not can_suspend(status, usb, ipa, locked and hint, blanked,
                       any(stream.get('corked') is False for stream in streams)):
        return {'slept': False, 'reason': 'readiness, lock, display or audio guard'}
    assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
    if sys.argv[1:] == ['--check']:
        return {'slept': False, 'reason': 'ready; check only'}
    with open('/run/t630-wake-pattern-test.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        installed = False
        try:
            (iface / 'wowl_add_ptrn').write_text(PATTERN)
            installed = True
            time.sleep(.35)  # Let the initiating button-release event settle.
            os.sync()
            before_boot = time.clock_gettime(time.CLOCK_BOOTTIME)
            before_active = time.monotonic()
            # Lab safety net: at most five minutes asleep while wake support
            # continues to be validated. No persistent RTC clock adjustment.
            result = subprocess.run(['rtcwake', '-m', 'freeze', '-d', '/dev/rtc0', '-s', '300'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=330)
            slept = ((time.clock_gettime(time.CLOCK_BOOTTIME) - before_boot)
                     - (time.monotonic() - before_active))
            reason = Path('/sys/kernel/wakeup_reasons/last_resume_reason').read_text().strip()
            return {'slept': result.returncode == 0 and slept > .05,
                    'seconds': round(slept, 3), 'exit': result.returncode,
                    'power_wake': 'pon_kpdpwr_status' in reason, 'reason': reason}
        finally:
            try:
                subprocess.run(['rtcwake', '-m', 'disable', '-d', '/dev/rtc0'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            finally:
                if installed:
                    (iface / 'wowl_del_ptrn').write_text(PATTERN)


if __name__ == '__main__':
    try:
        answer = main()
    except Exception as exc:
        answer = {'slept': False, 'reason': type(exc).__name__}
    print(json.dumps(answer), flush=True)
