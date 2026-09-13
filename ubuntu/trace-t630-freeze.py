#!/usr/bin/env python3
"""Bounded private trace instance: power events only, no input or packet data."""
import pathlib
import subprocess
import time

assert pathlib.Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
root = pathlib.Path('/run/t630-trace/instances/t630-sleep-test')
root.mkdir()  # Refuse to reuse someone else's instance.
try:
    (root / 'tracing_on').write_text('0')
    (root / 'buffer_size_kb').write_text('128')
    for name in ('wakeup_source_activate', 'wakeup_source_deactivate',
                 'suspend_resume', 'device_pm_callback_start',
                 'device_pm_callback_end'):
        (root / 'events' / 'power' / name / 'enable').write_text('1')
    (root / 'tracing_on').write_text('1')
    time.sleep(2)
    subprocess.run(['sh', '/run/test-t630-freeze.sh'], timeout=60)
    time.sleep(1)
finally:
    (root / 'tracing_on').write_text('0')
    pathlib.Path('/var/log/t630-freeze-power.trace').write_text(
        (root / 'trace').read_text())
    (root / 'events' / 'enable').write_text('0')
    root.rmdir()
