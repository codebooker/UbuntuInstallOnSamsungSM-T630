#!/usr/bin/python3
"""Map this SM-T630's Active and Recents keys into the nested X11 keycode range.

No event grab or input-reading daemon. --restore restores the stock keycode.
"""
import argparse
import fcntl
import os
from pathlib import Path
import struct

GET_KEYCODE = 0x80284504
SET_KEYCODE = 0x40284504
STOCK = 252
MAPPED = 184  # KEY_F14 -> XF86Launch5 in this desktop's evdev XKB map.
RECENTS_STOCK = 254
RECENTS_MAPPED = 185  # KEY_F15 -> XF86Launch6.


def key_entry(fd, index):
    data = bytearray(struct.pack('BBHI32s', 1, 0, index, 0, b''))
    fcntl.ioctl(fd, GET_KEYCODE, data, True)
    return struct.unpack('BBHI32s', data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--restore', action='store_true')
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if os.getuid() != 0:
        raise RuntimeError('Run as root.')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise RuntimeError('Not the validated tablet installation.')
    dt_code = Path('/sys/firmware/devicetree/base/soc/gpio_keys/hot_key/linux,code')
    if int.from_bytes(dt_code.read_bytes(), 'big') != STOCK:
        raise RuntimeError('Unexpected Active-key device tree; leaving keys unchanged.')
    devices = [p for p in Path('/sys/class/input').glob('event*')
               if (p / 'device/name').read_text().strip() == 'gpio_keys']
    if len(devices) != 1:
        raise RuntimeError('Expected exactly one gpio_keys device.')
    with open('/run/t630-red-button.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fd = os.open('/dev/input/' + devices[0].name, os.O_RDWR | os.O_CLOEXEC)
        try:
            before = [key_entry(fd, index) for index in range(5)]
            codes = [entry[3] for entry in before]
            if ([codes[i] for i in (0, 2, 3)] != [115, 158, 172]
                    or codes[1] not in (RECENTS_STOCK, RECENTS_MAPPED)
                    or codes[4] not in (STOCK, MAPPED)):
                raise RuntimeError(f'Unexpected keymap {codes}; leaving keys unchanged.')
            targets = {1: RECENTS_STOCK if args.restore else RECENTS_MAPPED,
                       4: STOCK if args.restore else MAPPED}
            if not args.check:
                try:
                    for index, target in targets.items():
                        if codes[index] != target:
                            fcntl.ioctl(fd, SET_KEYCODE,
                                        struct.pack('BBHI32s', 1, 0, index, target, b''))
                    after = [key_entry(fd, index) for index in range(5)]
                    if (any(after[i] != before[i] for i in (0, 2, 3))
                            or any(after[i][3] != target for i, target in targets.items())):
                        raise RuntimeError('Keymap verification failed.')
                except Exception:
                    for index in targets:
                        fcntl.ioctl(fd, SET_KEYCODE,
                                    struct.pack('BBHI32s', 1, 0, index, codes[index], b''))
                    raise
            print(f'Active={key_entry(fd, 4)[3]}, Recents={key_entry(fd, 1)[3]}; '
                  'volume, Back and Home keycodes unchanged.')
        finally:
            os.close(fd)


if __name__ == '__main__':
    main()
