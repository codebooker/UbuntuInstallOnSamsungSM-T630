#!/usr/bin/env python3
"""One guarded, temporary no-WoWLAN freeze test; restore exact known policy."""
import pathlib
import subprocess
import sys
import time


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True,
                          timeout=10).stdout.strip()


def wake_events():
    events = {}
    for node in pathlib.Path('/sys/class/wakeup').glob('wakeup*'):
        try:
            events[node.name + ':' + (node / 'name').read_text().strip()] = int(
                (node / 'event_count').read_text())
        except (OSError, ValueError):
            continue
    return events


assert pathlib.Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
assert pathlib.Path('/sys/class/power_supply/battery/status').read_text().strip() == 'Discharging'
assert all(p.read_text().strip() == 'not attached'
           for p in pathlib.Path('/sys/class/udc').glob('*/state'))
original = run('iw', 'phy', 'phy0', 'wowlan', 'show')
assert [line.strip() for line in original.splitlines()] == [
    'WoWLAN is enabled:', '* wake up on magic packet'], repr(original)
print('Before:', original, flush=True)
selective = bool(sys.argv[1:]) and sys.argv[1] == '--selective'
assert sys.argv[1:] in ([], ['--selective'], ['--selective', '--retry-busy'])
try:
    if selective:
        # Explicit Ethernet WoL pattern replaces vendor automatic patterns in
        # related Qualcomm PMO code; test this behavior, do not assume it works.
        mac = pathlib.Path('/sys/class/net/wlan0/address').read_text().strip()
        assert len(mac.split(':')) == 6
        pattern = mac + ':-:-:-:-:-:-:08:42'
        run('iw', 'phy', 'phy0', 'wowlan', 'enable', 'magic-packet',
            'patterns', pattern)
    else:
        run('iw', 'phy', 'phy0', 'wowlan', 'disable')
    current = run('iw', 'phy', 'phy0', 'wowlan', 'show')
    print('Temporary:', current, flush=True)
    if not selective:
        assert current == 'WoWLAN is disabled.'
    time.sleep(3)
    attempts = 3 if '--retry-busy' in sys.argv else 1
    for attempt in range(attempts):
        before_events = wake_events()
        failures = pathlib.Path('/sys/power/suspend_stats/fail')
        before_failures = int(failures.read_text())
        print('Attempt:', attempt + 1, flush=True)
        result = subprocess.run(['sh', '/run/test-t630-freeze.sh'], timeout=60)
        print('Freeze helper exit:', result.returncode, flush=True)
        print('Wake event deltas:', {name: count - before_events.get(name, 0)
              for name, count in wake_events().items()
              if count != before_events.get(name, 0)}, flush=True)
        if result.returncode == 0:
            break
        # Only retry a kernel-recorded EBUSY, never a failed safety guard.
        if (int(failures.read_text()) <= before_failures or
                pathlib.Path('/sys/power/suspend_stats/last_failed_errno').read_text().strip() != '-16'):
            break
        time.sleep(1.13 + attempt * 0.17)
finally:
    run('iw', 'phy', 'phy0', 'wowlan', 'enable', 'magic-packet')
    restored = run('iw', 'phy', 'phy0', 'wowlan', 'show')
    print('Restored:', restored, flush=True)
    assert restored == original
