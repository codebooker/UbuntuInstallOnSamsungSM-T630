"""Download a small screenshot in framed chunks and verify its full hash."""
import base64
import hashlib
import argparse
import re
from pathlib import Path
from serial_link import Link

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--name',default='persistent-scanout.png')
a = p.parse_args()
assert re.fullmatch(r'[a-z0-9-]+\.png',a.name)
target = root / 'reports' / a.name
assert not target.exists()
remote = '/run/ubuntu/tmp/t630-scanout.png'
with Link() as link:
    result = link.run(f'stat -c %s {remote}; sha256sum {remote}')
    assert 'REMOTE_EXIT=0' in result
    size, digest = int(result.splitlines()[0]), result.splitlines()[1].split()[0]
    assert 0 < size < 2*1024*1024
    content = bytearray()
    for block in range((size + 4095)//4096):
        result = link.run(f'dd if={remote} bs=4096 skip={block} count=1 2>/dev/null | base64')
        assert 'REMOTE_EXIT=0' in result
        content.extend(base64.b64decode(result.split('REMOTE_EXIT=')[0]))
assert len(content) == size and hashlib.sha256(content).hexdigest() == digest
with target.open('xb') as f:
    f.write(content)
print(f'Verified {size} bytes: {digest}')
