"""Stage authenticated Ubuntu package indexes for offline native apt resolution."""
import concurrent.futures
import hashlib
import io
import lzma
from pathlib import Path
import tarfile
import urllib.request
from serial_link import Link

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ports.ubuntu.com/ubuntu-ports/'
cache = ROOT / 'ubuntu/desktop-indexes'
cache.mkdir(exist_ok=True)

def fetch(rel):
    path = cache / rel.replace('/', '_')
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(BASE + rel, timeout=60).read())
    return path.read_bytes()

with Link() as link:
    entries = {}
    for suite in ('noble', 'noble-updates'):
        release = fetch(f'dists/{suite}/InRelease')
        remote = f'/run/ubuntu/tmp/desktop-{suite}-InRelease'
        link.upload_ram(release, remote)
        result = link.run(f'chroot /run/ubuntu gpgv --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg /tmp/desktop-{suite}-InRelease')
        print(result, flush=True)
        assert 'Good signature' in result and 'REMOTE_EXIT=0' in result
        (ROOT / f'reports/desktop-{suite}-signature.txt').write_text(result)
        hashes = {}
        for line in release.decode().split('SHA256:\n', 1)[1].split('\nSHA512:', 1)[0].splitlines():
            fields = line.split()
            if len(fields) == 3 and len(fields[0]) == 64:
                hashes[fields[2]] = fields[0]
        components = ('main', 'universe')
        paths = [f'{c}/binary-arm64/Packages.xz' for c in components]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            blobs = list(pool.map(fetch, [f'dists/{suite}/{p}' for p in paths]))
        prefix = f'ports.ubuntu.com_ubuntu-ports_dists_{suite}_'
        entries[prefix + 'InRelease'] = release
        for path, blob in zip(paths, blobs):
            assert hashlib.sha256(blob).hexdigest() == hashes[path]
            entries[prefix + path.replace('/', '_').removesuffix('.xz')] = lzma.decompress(blob)
            print(f'Authenticated {suite}/{path}: {len(blob)} bytes', flush=True)
    bundle = io.BytesIO()
    with tarfile.open(fileobj=bundle, mode='w:gz') as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o644
            tar.addfile(info, io.BytesIO(data))
    payload = bundle.getvalue()
    (cache / 'apt-lists.tar.gz').write_bytes(payload)
    link.upload_ram(payload, '/run/ubuntu/tmp/desktop-apt-lists.tar.gz')
    result = link.run('set -e; tar -xzf /run/ubuntu/tmp/desktop-apt-lists.tar.gz -C /run/ubuntu/var/lib/apt/lists; chroot /run/ubuntu apt-get --print-uris --yes --no-install-recommends install weston seatd udev libinput-tools fonts-dejavu-core', timeout=60)
    (ROOT / 'reports/desktop-apt-plan.txt').write_text(result)
    print(result, flush=True)
    assert 'REMOTE_EXIT=0' in result
