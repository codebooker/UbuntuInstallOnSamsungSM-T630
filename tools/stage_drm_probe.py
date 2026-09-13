"""Install signed Ubuntu display-query tools in the RAM-only Ubuntu root."""
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile
import urllib.request
from serial_link import Link

root = Path(__file__).resolve().parents[1]
release_path = root / 'ubuntu/noble-updates-InRelease'
release = release_path.read_text()
indexes = {
    'main/binary-arm64/Packages.xz': root / 'stock/noble-updates-main-arm64-Packages.xz',
    'universe/binary-arm64/Packages.xz': root / 'ubuntu/noble-updates-universe-arm64-Packages.xz',
}
section = release.split('SHA256:\n', 1)[1].split('\nSHA512:', 1)[0]
hashes = {}
for line in section.splitlines():
    fields = line.split()
    if len(fields) == 3 and len(fields[0]) == 64:
        hashes[fields[2]] = fields[0]
needed = {'libdrm-common', 'libdrm2', 'libdrm-tests', 'libdrm-amdgpu1',
          'libdrm-etnaviv1', 'libdrm-tegra0'}
packages = {}
for name, path in indexes.items():
    blob = path.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == hashes[name], f'Stale/invalid index: {name}'
    for paragraph in lzma.decompress(blob).decode().split('\n\n'):
        values = dict(line.split(': ', 1) for line in paragraph.splitlines()
                      if not line.startswith(' ') and ': ' in line)
        if values.get('Package') in needed:
            packages[values['Package']] = values
assert packages.keys() == needed
assert len({v['Version'] for v in packages.values()}) == 1

with Link() as link:
    link.upload_ram(release_path.read_bytes(), '/run/ubuntu/tmp/noble-updates-InRelease')
    verified = link.run('chroot /run/ubuntu /usr/bin/gpgv --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg /tmp/noble-updates-InRelease')
    print(verified, flush=True)
    assert 'REMOTE_EXIT=0' in verified and 'Good signature' in verified
    (root / 'reports/ubuntu-archive-signature.txt').write_text(verified)
    bundle = io.BytesIO()
    manifest = []
    with tarfile.open(fileobj=bundle, mode='w') as archive:
        for name, pkg in sorted(packages.items()):
            filename = pkg['Filename']
            assert filename.startswith(('pool/main/libd/libdrm/', 'pool/universe/libd/libdrm/'))
            payload = urllib.request.urlopen('https://ports.ubuntu.com/ubuntu-ports/' + filename, timeout=30).read()
            assert len(payload) == int(pkg['Size'])
            assert hashlib.sha256(payload).hexdigest() == pkg['SHA256']
            entry = tarfile.TarInfo(Path(filename).name)
            entry.size, entry.mode, entry.mtime = len(payload), 0o644, 0
            archive.addfile(entry, io.BytesIO(payload))
            manifest.append({'name': name, 'version': pkg['Version'], 'filename': filename, 'sha256': pkg['SHA256']})
    (root / 'ubuntu/drm-tools.tar').write_bytes(bundle.getvalue())
    (root / 'reports/drm-package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    link.upload_ram(bundle.getvalue(), '/run/ubuntu/tmp/drm-tools.tar')
    install = link.run('set -e; mkdir /run/ubuntu/tmp/drm-packages; tar -xf /run/ubuntu/tmp/drm-tools.tar -C /run/ubuntu/tmp/drm-packages; chroot /run/ubuntu /bin/bash -c "dpkg -i /tmp/drm-packages/*.deb"', timeout=40)
    print(install, flush=True)
    (root / 'reports/drm-tools-install.txt').write_text(install)
    assert 'REMOTE_EXIT=0' in install
    probe = link.run('set -e; mount --bind /dev /run/ubuntu/dev; chroot /run/ubuntu /usr/bin/modetest -D /dev/dri/card0 -c -p', timeout=30)
    (root / 'reports/drm-readonly-probe.txt').write_text(probe)
    print(probe[:7000])
