"""Remove generated Netplan credentials; verify all retained archive contents."""
import hashlib
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
source = root / 'output/ubuntu-desktop-ram-20260912-tls.tar.gz'
target = root / 'output/ubuntu-desktop-ram-20260912-sanitized.tar.gz'
if target.exists():
    assert target.stat().st_size == 0, 'Refusing to replace a nonempty artifact'
def excluded(name):
    path = name.removeprefix('./').rstrip('/')
    return any(path == p or path.startswith(p + '/') for p in (
        'etc/netplan', 'etc/NetworkManager/system-connections',
        'var/lib/NetworkManager', 'run', 'tmp', 'root/.bash_history'))

expected = {}
removed = 0
with tarfile.open(str(source), 'r|gz') as src, tarfile.open(str(target), 'w|gz') as dst:
    for member in src:
        if excluded(member.name):
            removed += 1
            continue
        stream = src.extractfile(member) if member.isfile() else None
        # Individual files are bounded userspace artifacts, not the whole root.
        import io
        data = stream.read() if stream else None
        expected[member.name] = (member.type, member.mode, member.uid, member.gid,
                                 member.linkname, hashlib.sha256(data or b'').hexdigest())
        dst.addfile(member, io.BytesIO(data) if data is not None else None)

seen = set()
with tarfile.open(str(target), 'r|gz') as archive:
    for member in archive:
        assert not excluded(member.name)
        stream = archive.extractfile(member) if member.isfile() else None
        h = hashlib.sha256()
        if stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        assert expected[member.name] == (member.type, member.mode, member.uid,
            member.gid, member.linkname, h.hexdigest()), member.name
        seen.add(member.name)
assert seen == expected.keys()
h = hashlib.sha256()
with target.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
report = {'artifact': str(target), 'sha256': h.hexdigest(), 'bytes': target.stat().st_size,
          'retained_entries_verified': len(seen), 'excluded_entries': removed,
          'note': 'Earlier snapshot accidentally included generated /etc/netplan; this sanitized replacement excludes it.'}
(root / 'reports/desktop-snapshot-sanitized.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
