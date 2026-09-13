#!/usr/bin/env python3
"""One reversible vendor-interface wake-pattern probe or guarded freeze."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time


def snapshot():
    count = 0
    for line in Path('/proc/interrupts').read_text().splitlines():
        if 'pm8xxx_rtc_alarm' in line:
            for field in line.split(':', 1)[1].split():
                if not field.isdigit():
                    break
                count += int(field)
    return {'boottime': time.clock_gettime(time.CLOCK_BOOTTIME),
            'monotonic': time.monotonic(), 'rtc_irqs': count}


assert os.geteuid() == 0
assert sys.argv[1:] in (['--probe'], ['--freeze'], ['--freeze-quiet'], ['--power-wake'])
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
assert os.uname().release == '5.4.274-qgki-31225846-abT630XXSBDZE3'
assert Path('/sys/bus/platform/devices/soc:qcom,ipa_fws/subsys0/state').read_text().strip() == 'ONLINE'
iface = Path('/sys/class/net/wlan0')
mac = (iface / 'address').read_text().strip()
assert len(mac.split(':')) == 6
freeze = sys.argv[1] != '--probe'
if freeze:
    assert Path('/sys/class/power_supply/battery/status').read_text().strip() == 'Discharging'
    states = list(Path('/sys/class/udc').glob('*/state'))
    assert states and all(p.read_text().strip() == 'not attached' for p in states)
    active = subprocess.check_output([
        '/usr/local/bin/t630-gnome-run', 'timeout', '5', 'gdbus', 'call', '--session',
        '--dest', 'org.gnome.ScreenSaver', '--object-path', '/org/gnome/ScreenSaver',
        '--method', 'org.gnome.ScreenSaver.GetActive'], text=True).strip()
    assert active == '(true,)'

# Vendor parser: hex byte length, mask byte length, contiguous bytes, mask.
# This sysfs parser limits commands to32bytes. Match only own unicast MAC;
# directed traffic can still wake it, but broadcasts do not match this rule.
pattern = '06:01:' + mac.replace(':', '') + ':3f'
if sys.argv[1] in ('--freeze-quiet', '--power-wake'):
    # Diagnostic only: no valid Ethernet destination is the all-zero address.
    # Suppress packet-pattern wake while retaining the independent RTC alarm.
    pattern = '06:01:000000000000:3f'
with open('/run/t630-wake-pattern-test.lock', 'w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    installed = False
    try:
        (iface / 'wowl_add_ptrn').write_text(pattern)
        installed = True
        print('Vendor wake-pattern write accepted.', flush=True)
        time.sleep(2)
        if freeze:
            if sys.argv[1] == '--power-wake':
                # Reuse the existing lock/blank implementation and shared state,
                # so the live Power handler restores light rather than reblanking.
                import importlib.machinery
                import importlib.util
                loader = importlib.machinery.SourceFileLoader(
                    't630_power', '/usr/local/sbin/t630-power-button')
                spec = importlib.util.spec_from_loader(loader.name, loader)
                power = importlib.util.module_from_spec(spec)
                loader.exec_module(power)
                if not power.STATE.exists():
                    power.lock_and_blank()
            for attempt in range(3):
                failures = Path('/sys/power/suspend_stats/fail')
                before_failures = int(failures.read_text())
                before = snapshot()
                duration = '45' if sys.argv[1] == '--power-wake' else '15'
                result = subprocess.run(['sh', '/run/test-t630-freeze.sh', duration], timeout=90)
                after = snapshot()
                elapsed = after['boottime'] - before['boottime']
                active_elapsed = after['monotonic'] - before['monotonic']
                print({'attempt': attempt + 1, 'helper_exit': result.returncode,
                       'elapsed': elapsed, 'suspended_seconds': elapsed - active_elapsed,
                       'rtc_irq_delta': after['rtc_irqs'] - before['rtc_irqs']}, flush=True)
                if result.returncode == 0:
                    break
                if (int(failures.read_text()) <= before_failures or
                        Path('/sys/power/suspend_stats/last_failed_errno').read_text().strip() != '-16'):
                    break  # Never retry a failed prerequisite or another error.
                time.sleep(1.13 + attempt * 0.17)
    finally:
        if installed:
            (iface / 'wowl_del_ptrn').write_text(pattern)
            print('Exact test pattern removed; driver default patterns restored.', flush=True)
