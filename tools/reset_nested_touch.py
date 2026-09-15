#!/usr/bin/python3
"""Guarded reset of only the private Xwayland touchscreen bridge.

Default is read-only; --reset requires the physical touchscreen to be idle.
No physical-device disable, event grab/injection, or handwriting recording.
Run as USB administrator inside the selected tablet Ubuntu root.
Re-enumeration can invalidate cached GNOME input objects. This is a lab
diagnostic, not a supported recovery guarantee or startup/watchdog helper.
"""
import fcntl
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

RUN = '/usr/local/bin/t630-gnome-run'


def virtual_touch(text):
    matches = re.findall(r'(xwayland-touch:[0-9]+)\s+id=([0-9]+)', text)
    if len(matches) != 1:
        raise ValueError('Expected one private Xwayland touchscreen.')
    return matches[0][0], int(matches[0][1])


def physical_contacts():
    if Path('/sys/class/input/event5/device/name').read_text().strip() != 'sec_touchscreen':
        raise ValueError('Unexpected physical touchscreen.')
    fd = os.open('/dev/input/event5', os.O_RDONLY | os.O_CLOEXEC)
    try:
        # Query current slot state only: no event stream, coordinates, or grab.
        axis = bytearray(24)
        fcntl.ioctl(fd, (2 << 30) | (24 << 16) | (ord('E') << 8) | (0x40 + 0x2f), axis)
        _, minimum, maximum, _, _, _ = struct.unpack('@6i', axis)
        if minimum != 0 or not 0 <= maximum < 20:
            raise ValueError('Unexpected touchscreen slot range.')
        slots = bytearray(struct.pack('@' + 'i' * (maximum + 2), 0x39,
                                      *([-1] * (maximum + 1))))
        fcntl.ioctl(fd, (2 << 30) | (len(slots) << 16) | (ord('E') << 8) | 0x0a, slots)
        return sum(value >= 0 for value in struct.unpack('@' + 'i' * (maximum + 2), slots)[1:])
    finally:
        os.close(fd)


def main():
    if os.getuid() != 0 or sys.argv[1:] not in ([], ['--reset']):
        raise SystemExit('Run as USB administrator; optional --reset.')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise SystemExit('Refusing an unknown installation.')
    def xinput(*args):
        return subprocess.check_output([RUN, '/usr/bin/env', 'DISPLAY=:3',
            '/usr/bin/xinput', *map(str, args)], text=True, timeout=8,
            stderr=subprocess.DEVNULL)
    name, device = virtual_touch(xinput('--list', '--short'))
    classes = xinput('--list', '--long', device)
    if not all(label in classes for label in ('Abs MT Position X', 'Abs MT Position Y', 'Touch mode: direct')):
        raise SystemExit('Unexpected virtual touchscreen capabilities.')
    if not re.search(r'Device Enabled \([0-9]+\):\s+1\s*$', xinput('list-props', device), re.M):
        raise SystemExit('Virtual touchscreen is already disabled; refusing reset.')
    contacts = physical_contacts()
    print(f'Physical contacts={contacts}; private bridge={name}.', flush=True)
    if sys.argv[1:] != ['--reset']:
        return
    if contacts:
        raise SystemExit('Lift all fingers before resetting; no change made.')
    print('Lab diagnostic: GNOME may retain a disposed input object after reset; '
          'a guarded session restart may be required.', flush=True)
    try:
        xinput('disable', device)
    finally:
        xinput('enable', device)
    if virtual_touch(xinput('--list', '--short')) != (name, device):
        raise SystemExit('Virtual touchscreen identity changed; inspect before further action.')
    if not re.search(r'Device Enabled \([0-9]+\):\s+1\s*$', xinput('list-props', device), re.M):
        raise SystemExit('Virtual touchscreen did not report re-enabled.')
    print('Private touch bridge re-enabled; physical responsiveness requires confirmation.')


if __name__ == '__main__':
    main()
