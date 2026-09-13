"""Make exact stock vendor drivers accessible through a read-only RAM image."""
import gzip
import hashlib
from pathlib import Path
from serial_link import Link

root = Path(__file__).resolve().parents[1]
source = root / 'stock/vendor.img'
data = source.read_bytes()
digest = hashlib.sha256(data).hexdigest()
payload = gzip.compress(data, compresslevel=1, mtime=0)
print(f'Stock vendor: {len(data)} bytes, compressed {len(payload)} bytes', flush=True)
with Link() as link:
    result = link.run('set -e; mount -o remount,size=3g /run; test ! -e /run/stock-vendor.img; test ! -e /run/stock-vendor')
    assert 'REMOTE_EXIT=0' in result
    link.upload_ram(payload, '/run/stock-vendor.img.gz')
    result = link.run(f'set -e; gzip -d /run/stock-vendor.img.gz; echo "{digest}  /run/stock-vendor.img" | sha256sum -c -; mkdir /run/stock-vendor; mount -t f2fs -o loop,ro /run/stock-vendor.img /run/stock-vendor; ls /run/stock-vendor/lib/modules; ls /run/stock-vendor/firmware', timeout=60)
    print(result, flush=True)
    (root / 'reports/stock-vendor-ram.txt').write_text(result)
    assert 'REMOTE_EXIT=0' in result
