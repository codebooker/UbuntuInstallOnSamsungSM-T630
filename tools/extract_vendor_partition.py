"""Read AOSP sparse/LP metadata and extract only vendor from local stock super."""
import bisect
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
f = (ROOT / 'stock/super.img').open('rb')
header = f.read(28)
magic, major, minor, fh, ch, block, blocks, chunks, crc = struct.unpack('<I4H4I', header)
assert magic == 0xed26ff3a and major == 1 and fh >= 28 and ch >= 12
spans, starts, logical = [], [], 0
f.seek(fh)
for _ in range(chunks):
    h = f.read(ch)
    kind, _, count, total = struct.unpack_from('<HHII', h)
    payload = total-ch
    length = count*block
    pos = f.tell()
    assert kind in (0xcac1, 0xcac2, 0xcac3, 0xcac4)
    if kind == 0xcac1: assert payload == length
    if kind == 0xcac2: assert payload == 4
    if length:
        starts.append(logical)
        spans.append((logical, length, kind, pos))
        logical += length
    f.seek(payload, 1)
assert logical == blocks*block

def read(offset, size):
    out = bytearray()
    while size:
        start, length, kind, pos = spans[bisect.bisect_right(starts, offset)-1]
        within = offset-start
        n = min(size, length-within)
        assert n > 0
        if kind == 0xcac1:
            f.seek(pos+within); part = f.read(n)
        elif kind == 0xcac2:
            f.seek(pos); fill = f.read(4)
            part = (fill*((n+7)//4))[within%4:within%4+n]
        else:
            part = bytes(n)
        assert len(part) == n
        out.extend(part); offset += n; size -= n
    return bytes(out)

geometry = read(4096, 52)
assert struct.unpack_from('<I', geometry)[0] == 0x616c4467
gsize = struct.unpack_from('<I', geometry, 4)[0]
assert gsize == 52
assert hashlib.sha256(geometry[:8]+bytes(32)+geometry[40:]).digest() == geometry[8:40]
h = read(12288, 128)
assert struct.unpack_from('<I', h)[0] == 0x414c5030
hsize = struct.unpack_from('<I', h, 8)[0]
h = read(12288, hsize)
assert hashlib.sha256(h[:12]+bytes(32)+h[44:]).digest() == h[12:44]
tables = read(12288+hsize, struct.unpack_from('<I', h, 44)[0])
assert hashlib.sha256(tables).digest() == h[48:80]
po, pn, ps = struct.unpack_from('<III', h, 80)
eo, en, es = struct.unpack_from('<III', h, 92)
assert ps == 52 and es == 24
manifest = []
for i in range(pn):
    name, attrs, first, count, group = struct.unpack_from('<36sIIII', tables, po+i*ps)
    name = name.rstrip(b'\0').decode()
    extents = [struct.unpack_from('<QIQI', tables, eo+j*es) for j in range(first, first+count)]
    item = dict(name=name, attributes=attrs, bytes=sum(e[0]*512 for e in extents), extents=extents)
    manifest.append(item)
    print(item, flush=True)
    if name not in ('vendor', 'vendor_a'): continue
    target = ROOT / f'stock/{name}.img'
    with target.open('xb') as out:
        for sectors, kind, sector, source in extents:
            assert kind == 0 and source == 0
            offset, remain = sector*512, sectors*512
            while remain:
                n = min(remain, 4*1024*1024)
                out.write(read(offset, n))
                offset += n; remain -= n
    print(f'Extracted {target}', flush=True)
(ROOT / 'reports/stock-super-partitions.json').write_text(json.dumps(manifest, indent=2))
