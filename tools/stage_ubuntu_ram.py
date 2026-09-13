"""Transfer the verified Ubuntu Base archive into tablet RAM; no flash/mount."""
import hashlib
from pathlib import Path
from serial_link import Link

root = Path(__file__).resolve().parents[1]
data = (root / 'ubuntu/ubuntu-base-24.04.5-base-arm64.tar.gz').read_bytes()
assert hashlib.sha256(data).hexdigest() == 'a91d5a93010193712d346d761372b7c9db6dfcf093893161c64ca107f05914f2'
with Link() as link:
    print('Testing binary transfer with a 1-MiB sample', flush=True)
    link.upload_ram(data[:1024*1024], '/run/ubuntu-transfer-probe.bin')
    result = link.upload_ram(data, '/run/ubuntu-base-24.04.5-arm64.tar.gz')
    (root / 'reports/ubuntu-ram-transfer.txt').write_text(result)
