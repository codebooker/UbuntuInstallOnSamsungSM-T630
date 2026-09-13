"""Bounded evdev pen-path test. Does NOT verify the physical digitizer.

Only the owner's integrated pen event node; refuse a currently held tip.
Releases all synthesized state even on exceptions. No device grab or keyboard.
"""
import fcntl
import os
import struct
import time
import argparse

p = argparse.ArgumentParser()
p.add_argument('--x-fraction', type=float, default=.5)
p.add_argument('--y-fraction', type=float, default=.5)
a = p.parse_args()
assert .1 <= a.x_fraction <= .85 and .1 <= a.y_fraction <= .85

path = '/dev/input/event7'
assert open('/sys/class/input/event7/device/name').read().strip() == 'sec_e-pen'
def ior(number, size):
    return (2 << 30) | (size << 16) | (ord('E') << 8) | number
def absinfo(fd, axis):
    data = bytearray(24)
    fcntl.ioctl(fd, ior(0x40 + axis,24), data)
    return struct.unpack('6i', data)
fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
xinfo, yinfo, pressure = absinfo(fd,0), absinfo(fd,1), absinfo(fd,24)
assert pressure[0] == 0, 'Physical pen is in use; do not inject'
keys = bytearray(96)
fcntl.ioctl(fd, ior(0x18,96), keys)
assert not keys[330//8] & (1 << (330%8)), 'Physical tip is down'
assert struct.calcsize('@llHHi') == 24
def send(kind, code, value):
    timestamp = time.time()
    os.write(fd, struct.pack('@llHHi', int(timestamp), int(timestamp%1*1e6), kind, code, value))
def sync(): send(0,0,0)
x = xinfo[1] + int((xinfo[2]-xinfo[1]) * a.x_fraction)
y = yinfo[1] + int((yinfo[2]-yinfo[1]) * a.y_fraction)
try:
    send(1,320,1); send(3,0,x); send(3,1,y); send(3,24,0); sync()
    time.sleep(.5)
    send(3,24,pressure[2]//2); send(1,330,1); sync()
    time.sleep(.2)
    for step in range(1,11):
        send(3,0,x + (xinfo[2]-xinfo[1])*step//100)
        send(3,1,y + (yinfo[2]-yinfo[1])*step//100)
        sync(); time.sleep(.05)
finally:
    send(1,330,0); send(3,24,0); sync()
    send(1,320,0); sync()
    os.close(fd)
print('Synthetic pen sequence completed and released; physical sensor untested.')
