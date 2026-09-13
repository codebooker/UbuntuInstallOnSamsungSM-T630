"""Download the native apt plan, check signed-index SHA256s, and install in RAM."""
import concurrent.futures
import hashlib
import io
import json
import lzma
from pathlib import Path
import shlex
import tarfile
import urllib.parse
import urllib.request
from serial_link import Link

ROOT = Path(__file__).resolve().parents[1]
records = {}
for path in (ROOT / 'ubuntu/desktop-indexes').glob('*Packages.xz'):
    for stanza in lzma.decompress(path.read_bytes()).decode().split('\n\n'):
        p = dict(l.split(': ', 1) for l in stanza.splitlines() if not l.startswith(' ') and ': ' in l)
        if 'Filename' in p:
            records[p['Filename']] = p
downloads = []
for line in (ROOT / 'reports/desktop-apt-plan.txt').read_text().splitlines():
    if not line.startswith("'http://ports.ubuntu.com/ubuntu-ports/pool/"):
        continue
    url, filename, size, _ = shlex.split(line)
    rel = urllib.parse.unquote(url.split('/ubuntu-ports/', 1)[1])
    p = records[rel]
    assert int(size) == int(p['Size'])
    downloads.append((url.replace('http:', 'https:', 1), filename, p))
cache = ROOT / 'ubuntu/desktop-debs'
cache.mkdir(exist_ok=True)

def download(item):
    url, filename, p = item
    path = cache / filename
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(url, timeout=90).read())
    data = path.read_bytes()
    assert len(data) == int(p['Size']) and hashlib.sha256(data).hexdigest() == p['SHA256'], filename
    return filename, data

print(f'Downloading and verifying {len(downloads)} packages', flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    payloads = list(pool.map(download, downloads))
(ROOT / 'reports/desktop-package-manifest.json').write_text(json.dumps([p for _, _, p in downloads], indent=2))
print(f'{sum(len(d) for _, d in payloads)} bytes authenticated', flush=True)
bundle = io.BytesIO()
with tarfile.open(fileobj=bundle, mode='w') as tar:
    for name, data in payloads:
        info = tarfile.TarInfo(name)
        info.size, info.mode = len(data), 0o644
        tar.addfile(info, io.BytesIO(data))
with Link() as link:
    link.upload_ram(bundle.getvalue(), '/run/ubuntu/tmp/desktop-packages.tar')
    # Prevent service auto-start in the diagnostic chroot. No host storage changes.
    link.upload_ram(b'#!/bin/sh\nexit 101\n', '/run/ubuntu/usr/sbin/policy-rc.d')
    setup = link.run('set -e; chmod 755 /run/ubuntu/usr/sbin/policy-rc.d; mount --bind /proc /run/ubuntu/proc; mount --bind /sys /run/ubuntu/sys; mkdir -p /run/ubuntu/dev/shm; mount -t tmpfs -o size=256m tmpfs /run/ubuntu/dev/shm; tar -xf /run/ubuntu/tmp/desktop-packages.tar -C /run/ubuntu/var/cache/apt/archives')
    print(setup, flush=True)
    assert 'REMOTE_EXIT=0' in setup
    # Run asynchronously; poll a RAM log instead of holding serial open during install.
    result = link.run("chroot /run/ubuntu /usr/bin/nohup /bin/sh -c 'DEBIAN_FRONTEND=noninteractive apt-get --yes --no-download --no-install-recommends install weston seatd udev libinput-tools fonts-dejavu-core > /tmp/desktop-install.log 2>&1; echo $? > /tmp/desktop-install.exit' </dev/null >/run/desktop-install-launch.log 2>&1 &")
    print(result, flush=True)
