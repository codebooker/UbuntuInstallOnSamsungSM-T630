#!/usr/bin/python3
"""One synthetic short Power press through the actual monitor's input path.

This tests userspace integration, not the physical switch or its wake IRQ.
No input capture, authentication bypass, or persistent configuration changes.
"""
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

assert os.geteuid() == 0
assert sys.argv[1:] in (['--sleep'], ['--wake-display'])
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
assert os.uname().release == '5.4.274-qgki-31225846-abT630XXSBDZE3'
state = Path('/run/t630-display-off-brightness')
assert state.exists() == (sys.argv[1] == '--wake-display')
assert subprocess.check_output([
    '/usr/local/bin/t630-gnome-run', 'gdbus', 'call', '--session',
    '--dest', 'org.gnome.ScreenSaver', '--object-path', '/org/gnome/ScreenSaver',
    '--method', 'org.gnome.ScreenSaver.GetActive'], text=True, timeout=8).strip() == '(true,)'
if sys.argv[1] == '--sleep':
    assert Path('/etc/t630/suspend.enabled').exists()
    assert not Path('/etc/t630/suspend.disabled').exists()
    assert Path('/sys/class/power_supply/battery/status').read_text().strip() == 'Discharging'
    assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
candidates = [p for p in Path('/sys/class/input').glob('event*')
              if (p / 'device/name').read_text().strip() == 'qpnp_pon']
assert len(candidates) == 1
event = struct.Struct('@llHHi')
fd = os.open('/dev/input/' + candidates[0].name, os.O_WRONLY)
try:
    os.write(fd, event.pack(0, 0, 1, 116, 1) + event.pack(0, 0, 0, 0, 0))
    time.sleep(.1)
finally:
    os.write(fd, event.pack(0, 0, 1, 116, 0) + event.pack(0, 0, 0, 0, 0))
    os.close(fd)
print('Sent one 100 ms Power press; password lock unchanged.', flush=True)
