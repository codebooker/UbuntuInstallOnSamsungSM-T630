"""One bounded synthetic click on the verified 1920x1200 landscape desktop.

For setup UI checks only; this is not evidence of a physical digitizer test.
Refuses a pen currently in proximity or a finger down. Releases on exceptions.
"""
import argparse
import fcntl
import os
import struct
import time
p = argparse.ArgumentParser()
p.add_argument('x', type=int)
p.add_argument('y', type=int)
a = p.parse_args()
assert 0 <= a.x < 1920 and 0 <= a.y < 1200
assert open('/sys/class/input/event7/device/name').read().strip() == 'sec_e-pen'
assert open('/sys/class/input/event5/device/name').read().strip() == 'sec_touchscreen'
def ior(number, size): return (2<<30) | (size<<16) | (ord('E')<<8) | number
def keys(fd):
    value = bytearray(96)
    fcntl.ioctl(fd, ior(0x18, 96), value)
    return value
with open('/dev/input/event5', 'rb', buffering=0) as touch:
    bits = keys(touch.fileno())
    assert not bits[330//8] & (1<<(330%8)), 'Finger is down; refusing UI test'
fd = os.open('/dev/input/event7', os.O_RDWR | os.O_CLOEXEC)
def absolute(code):
    value = bytearray(24)
    fcntl.ioctl(fd, ior(0x40+code,24), value)
    return struct.unpack('6i', value)
bits = keys(fd)
assert not any(bits[k//8] & (1<<(k%8)) for k in (320,330)), 'Physical pen is in use'
xaxis,yaxis,pressure = absolute(0),absolute(1),absolute(24)
assert pressure[0] == 0
# Verified pen: positive raw Y maps to screen right; positive raw X maps up.
x = round(xaxis[1]+(xaxis[2]-xaxis[1])*(1-a.y/1200))
y = round(yaxis[1]+(yaxis[2]-yaxis[1])*(a.x/1920))
def send(kind,code,value):
    t = time.time()
    os.write(fd, struct.pack('@llHHi',int(t),int(t%1*1e6),kind,code,value))
def sync(): send(0,0,0)
try:
    send(1,320,1);send(3,0,x);send(3,1,y);send(3,24,0);sync()
    time.sleep(.15)
    send(3,24,pressure[2]//2);send(1,330,1);sync()
    time.sleep(.12)
finally:
    send(1,330,0);send(3,24,0);sync();send(1,320,0);sync()
    os.close(fd)
print('Synthetic UI click sent and fully released.')
