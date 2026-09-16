#!/usr/bin/python3
"""Suppress the SM-T630 touchscreen only while the S Pen is in proximity.

Reads the exact pen event node without an exclusive input grab. Coordinates, pressure, and
touch events are discarded without logging. The exact touchscreen sysfs control
is restored to enabled on every ordinary exit.
"""

import ctypes
import fcntl
import os
from pathlib import Path
import select
import signal
import struct


INSTALL_ID = 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
PEN_EVENT = Path('/dev/input/event7')
PEN_NAME = Path('/sys/class/input/event7/device/name')
TOUCH_NAME = Path('/sys/class/input/event5/device/name')
TOUCH_ENABLED = Path('/sys/class/input/event5/device/enabled')
LOCK = Path('/run/t630-pen-touch-guard.lock')
EVENT = struct.Struct('@llHHi')
EV_KEY = 0x01
SYN_DROPPED = (0x00, 0x03)
BTN_TOOL_PEN = 0x140
BTN_TOOL_RUBBER = 0x141
KEY_BYTES = 96


def _eviocgkey(length):
    # Linux _IOR('E', 0x18, length), valid for the deployed arm64 ABI.
    return (2 << 30) | (length << 16) | (ord('E') << 8) | 0x18


def _pressed(keys, code):
    return bool(keys[code // 8] & (1 << (code % 8)))


def tool_in_proximity(fd):
    keys = bytearray(KEY_BYTES)
    fcntl.ioctl(fd, _eviocgkey(len(keys)), keys, True)
    return _pressed(keys, BTN_TOOL_PEN) or _pressed(keys, BTN_TOOL_RUBBER)


def set_touch_enabled(enabled):
    value = '1' if enabled else '0'
    current = TOUCH_ENABLED.read_text().strip()
    if current not in ('0', '1'):
        raise RuntimeError('Unexpected touchscreen enabled state')
    if current != value:
        TOUCH_ENABLED.write_text(value)
    if TOUCH_ENABLED.read_text().strip() != value:
        raise RuntimeError('Touchscreen state did not change')


def validate_device():
    if os.geteuid() != 0:
        raise RuntimeError('Guard must run as root')
    if Path('/etc/t630-install-id').read_text().strip() != INSTALL_ID:
        raise RuntimeError('Wrong device installation')
    if PEN_NAME.read_text().strip() != 'sec_e-pen':
        raise RuntimeError('Unexpected pen event node')
    if TOUCH_NAME.read_text().strip() != 'sec_touchscreen':
        raise RuntimeError('Unexpected touchscreen event node')
    if not PEN_EVENT.is_char_device() or not TOUCH_ENABLED.is_file():
        raise RuntimeError('Required input controls are unavailable')


def run():
    validate_device()
    ctypes.CDLL(None).prctl(15, b't630-pen-guard', 0, 0, 0)
    lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_CLOEXEC, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    pen_fd = os.open(PEN_EVENT, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    pending = bytearray()

    def stop(_signum, _frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        set_touch_enabled(not tool_in_proximity(pen_fd))
        while True:
            readable, _, _ = select.select([pen_fd], [], [], 2.0)
            if not readable:
                continue
            try:
                chunk = os.read(pen_fd, EVENT.size * 64)
            except BlockingIOError:
                continue
            if not chunk:
                raise RuntimeError('Pen event device closed')
            pending.extend(chunk)
            while len(pending) >= EVENT.size:
                packet = bytes(pending[:EVENT.size])
                del pending[:EVENT.size]
                _seconds, _micros, event_type, code, value = EVENT.unpack(packet)
                if (event_type, code) == SYN_DROPPED:
                    set_touch_enabled(not tool_in_proximity(pen_fd))
                elif event_type == EV_KEY and code in (BTN_TOOL_PEN, BTN_TOOL_RUBBER):
                    set_touch_enabled(value == 0 and not tool_in_proximity(pen_fd))
    finally:
        set_touch_enabled(True)
        os.close(pen_fd)
        os.close(lock_fd)


def main():
    run()


if __name__ == '__main__':
    main()
