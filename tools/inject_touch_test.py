"""Synthetic single-finger path test, not physical touchscreen verification."""
import fcntl
import os
import struct
import time
assert open('/sys/class/input/event5/device/name').read().strip() == 'sec_touchscreen'
def ior(number, size): return (2<<30) | (size<<16) | (ord('E')<<8) | number
fd = os.open('/dev/input/event5', os.O_RDWR | os.O_CLOEXEC)
def absinfo(axis):
    data = bytearray(24)
    fcntl.ioctl(fd, ior(0x40+axis,24), data)
    return struct.unpack('6i',data)
xinfo,yinfo = absinfo(0x35),absinfo(0x36)
keys = bytearray(96)
fcntl.ioctl(fd,ior(0x18,96),keys)
assert not keys[330//8] & (1<<(330%8)), 'Physical finger is down; do not inject'
def send(kind,code,value):
    t=time.time()
    os.write(fd,struct.pack('@llHHi',int(t),int(t%1*1e6),kind,code,value))
def sync(): send(0,0,0)
x=(xinfo[1]+xinfo[2])//2
y=(yinfo[1]+yinfo[2])//2
try:
    send(3,0x2f,0); send(3,0x39,12345)
    send(3,0x35,x); send(3,0x36,y); send(1,330,1); sync()
    time.sleep(.2)
    for step in range(1,11):
        send(3,0x35,x+(xinfo[2]-xinfo[1])*step//100)
        send(3,0x36,y+(yinfo[2]-yinfo[1])*step//100)
        sync();time.sleep(.05)
finally:
    send(3,0x2f,0); send(3,0x39,-1); send(1,330,0); sync()
    os.close(fd)
print('Synthetic single-finger sequence completed and released; sensor untested.')
