"""Resolve on native Ubuntu, fetch on Mac, SHA256-check, install only into RAM."""
import concurrent.futures
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import shlex
import sys
import tarfile
import urllib.parse
import urllib.request
from serial_link import Link

ROOT = Path(__file__).resolve().parents[1]
label, *packages = sys.argv[1:]
assert re.fullmatch(r'[a-z0-9-]+', label) and packages
assert all(re.fullmatch(r'[a-z0-9+.-]+', p) for p in packages)
args = ' '.join(packages)
with Link() as link:
    plan = link.run(f'chroot /run/ubuntu apt-get --print-uris --yes --no-install-recommends install {args}', timeout=40)
(ROOT / f'reports/{label}-apt-plan.txt').write_text(plan)
assert 'REMOTE_EXIT=0' in plan
records = {}
cache = ROOT / 'ubuntu/desktop-indexes'
for suite in ('noble', 'noble-updates'):
    release = (cache / f'dists_{suite}_InRelease').read_text()
    hashes = {}
    for line in release.split('SHA256:\n', 1)[1].split('\nSHA512:', 1)[0].splitlines():
        fields = line.split()
        if len(fields) == 3 and len(fields[0]) == 64: hashes[fields[2]] = fields[0]
    for component in ('main', 'universe'):
        path = f'{component}/binary-arm64/Packages.xz'
        data = (cache / f'dists_{suite}_{path.replace("/", "_")}').read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashes[path]
        for stanza in lzma.decompress(data).decode().split('\n\n'):
            p = dict(l.split(': ', 1) for l in stanza.splitlines() if not l.startswith(' ') and ': ' in l)
            if 'Filename' in p: records[p['Filename']] = p
downloads = []
for line in plan.splitlines():
    if not line.startswith("'http://ports.ubuntu.com/ubuntu-ports/pool/"): continue
    url, filename, size, _ = shlex.split(line)
    rel = urllib.parse.unquote(url.split('/ubuntu-ports/', 1)[1])
    p = records[rel]
    assert int(size) == int(p['Size'])
    downloads.append((url.replace('http:', 'https:', 1), filename, p))

def download(item):
    url, filename, p = item
    path = ROOT / 'ubuntu/desktop-debs' / filename
    if not path.exists(): path.write_bytes(urllib.request.urlopen(url, timeout=90).read())
    data = path.read_bytes()
    assert len(data) == int(p['Size']) and hashlib.sha256(data).hexdigest() == p['SHA256'], filename
    return filename, data

print(f'{label}: resolving {len(downloads)} packages', flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    payloads = list(pool.map(download, downloads))
(ROOT / f'reports/{label}-packages.json').write_text(json.dumps([p for _, _, p in downloads], indent=2))
bundle = io.BytesIO()
with tarfile.open(fileobj=bundle, mode='w') as tar:
    for name, data in payloads:
        info = tarfile.TarInfo(name); info.size, info.mode = len(data), 0o644
        tar.addfile(info, io.BytesIO(data))
with Link() as link:
    link.upload_ram(bundle.getvalue(), f'/run/ubuntu/tmp/{label}-packages.tar')
    result = link.run(f'set -e; tar -xf /run/ubuntu/tmp/{label}-packages.tar -C /run/ubuntu/var/cache/apt/archives; chroot /run/ubuntu /usr/bin/nohup /bin/sh -c "DEBIAN_FRONTEND=noninteractive apt-get --yes --no-download --no-install-recommends install {args} > /tmp/{label}-install.log 2>&1; echo \\$? > /tmp/{label}-install.exit" </dev/null >/run/{label}-launch.log 2>&1 &')
    print(result, flush=True)
