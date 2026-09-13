"""Single synthetic tap for the already calibrated 1920x1200 tablet desktop."""
import argparse
import fcntl
import os
import struct
import time
p=argparse.ArgumentParser()
p.add_argument('x',type=int);p.add_argument('y',type=int)
a=p.parse_args()
assert 0<=a.x<1920 and 0<=a.y<1200
assert open('/sys/class/input/event5/device/name').read().strip()=='sec_touchscreen'
def ior(n,size): return (2<<30)|(size<<16)|(ord('E')<<8)|n
fd=os.open('/dev/input/event5',os.O_RDWR|os.O_CLOEXEC)
bits=bytearray(96);fcntl.ioctl(fd,ior(0x18,96),bits)
assert not bits[330//8]&(1<<(330%8)), 'Finger is down; refusing test'
def axis(code):
    data=bytearray(24);fcntl.ioctl(fd,ior(0x40+code,24),data)
    return struct.unpack('6i',data)
ax,ay=axis(0x35),axis(0x36)
# Invert the currently installed -1 0 1 / 0 -1 1 libinput calibration,
# as well as Weston's landscape rotation. This changes only synthetic input.
x=round(ax[1]+(ax[2]-ax[1])*(1-a.y/1200))
y=round(ay[1]+(ay[2]-ay[1])*a.x/1920)
def send(kind,code,value):
    t=time.time();os.write(fd,struct.pack('@llHHi',int(t),int(t%1*1e6),kind,code,value))
try:
    send(3,0x2f,0);send(3,0x39,24680);send(3,0x35,x);send(3,0x36,y)
    send(1,330,1);send(0,0,0);time.sleep(.1)
finally:
    send(3,0x2f,0);send(3,0x39,-1);send(1,330,0);send(0,0,0)
    os.close(fd)
print('Synthetic touch tap completed and released.')
