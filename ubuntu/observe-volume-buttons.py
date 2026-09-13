#!/usr/bin/python3
"""Read-only bounded observer of physical volume keys; no grab or other key log."""
import os
from pathlib import Path
import select
import struct
import subprocess
import time
files = []
for entry in Path('/sys/class/input').glob('event*'):
    if (entry / 'device/name').read_text().strip() in ('gpio_keys', 'qpnp_pon'):
        files.append(os.open('/dev/input/' + entry.name, os.O_RDONLY | os.O_NONBLOCK))
assert len(files) == 2
event = struct.Struct('llHHi')
deadline = time.monotonic() + 35
try:
    while time.monotonic() < deadline:
        ready, _, _ = select.select(files, [], [], min(1, deadline - time.monotonic()))
        for fd in ready:
            data = os.read(fd, event.size * 32)
            for offset in range(0, len(data), event.size):
                _, _, kind, code, value = event.unpack_from(data, offset)
                if kind == 1 and code in (114, 115) and value == 1:
                    time.sleep(.15)
                    result = subprocess.check_output(['/usr/local/bin/t630-gnome-run', 'pactl',
                                                     'get-sink-volume', 't630_speakers'], text=True)
                    print(('Volume down' if code == 114 else 'Volume up') + ': ' + result.splitlines()[0], flush=True)
finally:
    for fd in files: os.close(fd)
