"""Bounded synthetic touch swipe through the tablet's calibrated input path."""
import argparse
import fcntl
import os
import struct
import time

p = argparse.ArgumentParser()
p.add_argument('x1', type=int)
p.add_argument('y1', type=int)
p.add_argument('x2', type=int)
p.add_argument('y2', type=int)
p.add_argument('--duration', type=float, default=.4)
a = p.parse_args()
assert 0 <= a.x1 < 1920 and 0 <= a.x2 < 1920
assert 0 <= a.y1 < 1200 and 0 <= a.y2 < 1200
assert .2 <= a.duration <= 5
assert open('/sys/class/input/event5/device/name').read().strip() == 'sec_touchscreen'

def ior(n, size):
    return (2 << 30) | (size << 16) | (ord('E') << 8) | n

fd = os.open('/dev/input/event5', os.O_RDWR | os.O_CLOEXEC)
bits = bytearray(96)
fcntl.ioctl(fd, ior(0x18, 96), bits)
assert not bits[330 // 8] & (1 << (330 % 8)), 'Finger is down; refusing test'

def axis(code):
    data = bytearray(24)
    fcntl.ioctl(fd, ior(0x40 + code, 24), data)
    return struct.unpack('6i', data)

ax, ay = axis(0x35), axis(0x36)

def send(kind, code, value):
    t = time.time()
    os.write(fd, struct.pack('@llHHi', int(t), int(t % 1 * 1e6), kind, code, value))

def position(x, y):
    # Inverse of the verified libinput flip and landscape output rotation.
    send(3, 0x35, round(ax[1] + (ax[2] - ax[1]) * (1 - y / 1200)))
    send(3, 0x36, round(ay[1] + (ay[2] - ay[1]) * x / 1920))

try:
    send(3, 0x2f, 0)
    send(3, 0x39, 24681)
    position(a.x1, a.y1)
    send(1, 330, 1)
    send(0, 0, 0)
    for step in range(1, 21):
        time.sleep(a.duration / 20)
        position(a.x1 + (a.x2 - a.x1) * step / 20,
                 a.y1 + (a.y2 - a.y1) * step / 20)
        send(0, 0, 0)
finally:
    send(3, 0x2f, 0)
    send(3, 0x39, -1)
    send(1, 330, 0)
    send(0, 0, 0)
    os.close(fd)
print('Synthetic swipe completed and released; not a sensor test.')
