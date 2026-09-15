#!/usr/bin/python3
"""Give Mutter's nested X11 backend explicit Xwayland tablet metadata.

No coordinate remapping, device grabs, input injection, or handwriting logging.
--refresh briefly re-enumerates the three virtual tools while the physical pen is idle.
--prepare sets tool types before Mutter enumerates devices; --publish-tool
publishes serials after Mutter is ready. Neither startup phase resets devices.
Call with DISPLAY=:3 and its existing XAUTHORITY. Live --refresh needs the
USB administrator for its read-only physical-pen idle check. This experiment
is not automatically installed/enabled by the pen-app recipe.
"""
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys


def tablet_devices(text):
    result = []
    for line in text.splitlines():
        match = re.search(r'(xwayland-tablet (stylus|eraser|cursor):[0-9]+)\s+id=([0-9]+)', line)
        if match:
            result.append((match.group(1), match.group(2), int(match.group(3))))
    if len(result) != 3 or len({kind for _, kind, _ in result}) != 3:
        raise ValueError('Expected exactly the private Xwayland stylus/eraser/cursor set.')
    return result


def pen_is_idle():
    if Path('/sys/class/input/event7/device/name').read_text().strip() != 'sec_e-pen':
        raise ValueError('Unexpected physical pen device.')
    fd = os.open('/dev/input/event7', os.O_RDONLY | os.O_CLOEXEC)
    try:
        keys = bytearray(96)
        request = (2 << 30) | (96 << 16) | (ord('E') << 8) | 0x18
        fcntl.ioctl(fd, request, keys)
        return not any(keys[key // 8] & (1 << (key % 8)) for key in (320, 330))
    finally:
        os.close(fd)


def main():
    if sys.argv[1:] not in ([], ['--refresh'], ['--prepare'], ['--publish-tool']) or os.environ.get('DISPLAY') != ':3':
        raise SystemExit('Run in the private :3 session; optional --prepare/--publish-tool/--refresh.')
    refresh = sys.argv[1:] == ['--refresh']
    if refresh and not pen_is_idle():
        raise SystemExit('Physical pen is in use; leave it off the screen and retry.')
    def xinput(*args):
        return subprocess.run(['/usr/bin/xinput', *map(str, args)], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=5).stdout
    devices = tablet_devices(xinput('--list', '--short'))
    for name, kind, device in devices:
        if 'Abs Pressure' not in xinput('--list', '--long', device):
            raise SystemExit('Expected pressure-capable tablet; refusing metadata changes.')
    for name, kind, device in devices:
        if sys.argv[1:] != ['--publish-tool']:
            xinput('set-prop', '--type=atom', '--format=32', device,
                   'Wacom Tool Type', kind.upper())
        if refresh:
            # Recreate the immutable Mutter device classification, not the
            # physical digitizer. Always re-enable on a failed refresh.
            try:
                xinput('disable', device)
            finally:
                xinput('enable', device)
        # Mutter's device-added path guesses only libinput serial metadata.
        # Publish Wacom serial AFTER re-enumeration so its property event sets
        # the current tool on the newly created device, not the destroyed one.
        if sys.argv[1:] != ['--prepare']:
            xinput('set-prop', '--type=int', '--format=32', device,
                   'Wacom Serial IDs', 0, 0, 0, 630)
    print('Private Xwayland tablet metadata configured; physical pressure acceptance pending.')


if __name__ == '__main__':
    main()
