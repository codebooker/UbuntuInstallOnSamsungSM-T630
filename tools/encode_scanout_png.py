"""Losslessly encode a raw PPM scanout capture as PNG, without altering pixels."""
import struct
import zlib
from pathlib import Path

with Path('/tmp/t630-scanout.ppm').open('rb') as f:
    assert f.readline() == b'P6\n'
    w, h = map(int, f.readline().split())
    assert f.readline() == b'255\n'
    pixels = f.read()
assert len(pixels) == w*h*3
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))
rows = b''.join(b'\0'+pixels[y*w*3:(y+1)*w*3] for y in range(h))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w,h,8,2,0,0,0))
png += chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')
with Path('/tmp/t630-scanout.png').open('xb') as f:
    f.write(png)
print(f'Encoded unchanged {w}x{h} pixels as {len(png)} PNG bytes')
