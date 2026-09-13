"""Use individually framed text-safe chunks for a trustworthy serial backup."""
import base64
import hashlib
from pathlib import Path
from serial_link import Link

root = Path(__file__).resolve().parents[1]
target = root / 'output/ubuntu-desktop-ram-20260912-verified.tar.gz'
source = '/run/ubuntu/tmp/desktop-snapshot.tar.gz'
with Link() as link:
    info = link.run(f'stat -c %s {source}; sha256sum {source}').splitlines()
    size, expected = int(info[0]), info[1].split()[0]
    chunk_size = 2*1024*1024
    digest = hashlib.sha256()
    with target.open('xb') as out:
        for index, offset in enumerate(range(0, size, chunk_size)):
            result = link.run(f'dd if={source} bs={chunk_size} skip={index} count=1 2>/dev/null | base64', timeout=30)
            assert 'REMOTE_EXIT=0' in result
            payload = base64.b64decode(result.split('REMOTE_EXIT=', 1)[0])
            assert len(payload) == min(chunk_size, size-offset)
            out.write(payload); digest.update(payload)
            if index % 8 == 7: print(f'Framed transfer: {(offset+len(payload))//(1024*1024)} MiB', flush=True)
    assert digest.hexdigest() == expected
    (root / 'reports/desktop-snapshot.sha256').write_text(expected+'  '+target.name+'\n')
    print(f'Complete: {size} bytes, SHA256 {expected}', flush=True)
