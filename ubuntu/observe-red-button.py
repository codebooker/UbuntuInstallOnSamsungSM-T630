#!/usr/bin/python3
"""Observe only the Active button for 45 seconds; never grab or log typed keys."""
import os
from pathlib import Path
import select
import struct
import time

devices = [p for p in Path('/sys/class/input').glob('event*')
           if (p / 'device/name').read_text().strip() == 'gpio_keys']
if len(devices) != 1:
    raise SystemExit('Expected one gpio_keys device.')
fd = os.open('/dev/input/' + devices[0].name, os.O_RDONLY | os.O_NONBLOCK)
event = struct.Struct('llHHi')
deadline = time.monotonic() + 45
print('Watching only Active-key events for 45 seconds.', flush=True)
try:
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], max(0, min(1, deadline - time.monotonic())))
        if not ready:
            continue
        data = os.read(fd, event.size * 32)
        for offset in range(0, len(data), event.size):
            _, _, kind, code, value = event.unpack_from(data, offset)
            if kind == 1 and code in (184, 252):
                print(f'Active key code={code} value={value}', flush=True)
finally:
    os.close(fd)
    print('Observer finished.', flush=True)
