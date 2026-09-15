#!/usr/bin/python3
"""Bounded read-only pressure-axis check of this tablet's exact known pen.

Queries current ABS_PRESSURE only. No event stream, coordinates, buttons,
grabs, input injection, sysfs inventory, or handwriting capture.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import struct
import time


def read_pressure(fd):
    axis = bytearray(24)
    request = (2 << 30) | (24 << 16) | (ord('E') << 8) | (0x40 + 0x18)
    fcntl.ioctl(fd, request, axis)
    value, minimum, maximum, _, _, _ = struct.unpack('@6i', axis)
    if minimum != 0 or not 1 <= maximum <= 65535 or not minimum <= value <= maximum:
        raise ValueError('Unexpected pen pressure range/value.')
    return value, maximum


def observe(seconds):
    if not 15 <= seconds <= 120:
        raise ValueError('Use a bounded 15–120 second observation.')
    if os.getuid() != 0:
        raise PermissionError('Use the existing USB administrator for this check.')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise ValueError('Unrecognized installation.')
    if Path('/sys/class/input/event7/device/name').read_text().strip() != 'sec_e-pen':
        raise ValueError('Unexpected physical pen device.')
    fd = os.open('/dev/input/event7', os.O_RDONLY | os.O_CLOEXEC)
    count = pressed = 0
    low = high = axis_max = None
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            value, maximum = read_pressure(fd)
            if axis_max is not None and axis_max != maximum:
                raise ValueError('Pen pressure axis range changed.')
            axis_max = maximum
            count += 1
            pressed += value > 0
            low = value if low is None else min(low, value)
            high = value if high is None else max(high, value)
            time.sleep(0.05)
    finally:
        os.close(fd)
    return dict(samples=count, pressed_samples=pressed, minimum=low,
                maximum=high, axis_maximum=axis_max)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=30)
    print(json.dumps(observe(parser.parse_args().seconds), sort_keys=True))
