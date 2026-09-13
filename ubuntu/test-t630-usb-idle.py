#!/usr/bin/python3
"""Temporarily disconnect only this lab serial gadget; always reconnect afterward."""
import os
from pathlib import Path
import subprocess
import sys
import time

assert os.getuid() == 0
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
gadget = Path('/proc/1/root/config/usb_gadget/t630_bringup')
udc = Path('/sys/class/udc/a600000.dwc3')
power = Path('/sys/devices/platform/soc/a600000.ssusb/power/runtime_status')
assert (gadget / 'UDC').read_text().strip() == 'a600000.dwc3'
assert (udc / 'function').read_text().strip() == 't630_bringup'
assert [p.name for p in (gadget / 'configs/c.1').iterdir() if p.is_symlink()] == ['acm.usb0']
assert (udc / 'state').read_text().strip() == 'configured'
test_host = os.environ.get('T630_TEST_HOST', '1.1.1.1')
assert subprocess.run(['ip', 'route', 'get', test_host], capture_output=True,
                      text=True, check=True).stdout.find('dev wlan0') >= 0
assert sys.argv[1:] in ([], ['--unbind'])
unbind = sys.argv[1:] == ['--unbind']
try:
    if unbind:
        (gadget / 'UDC').write_text('\n')
    else:
        (udc / 'soft_connect').write_text('disconnect')
    time.sleep(6)
    state = (udc / 'state').read_text().strip()
    runtime = power.read_text().strip()
    print('USB logical state:', state, 'controller runtime state:', runtime, flush=True)
    if runtime != 'suspended':
        print('Controller is still active; not attempting another suspend.', flush=True)
    else:
        assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
        result = subprocess.run(['sh', '/run/test-t630-freeze.sh'], timeout=50)
        print('Shallow sleep test exit:', result.returncode, flush=True)
finally:
    if unbind:
        current = (gadget / 'UDC').read_text().strip()
        if not current:
            (gadget / 'UDC').write_text('a600000.dwc3')
        else:
            assert current == 'a600000.dwc3'
    else:
        (udc / 'soft_connect').write_text('connect')
    print('USB serial data connection re-enabled.', flush=True)
