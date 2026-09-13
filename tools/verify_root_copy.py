"""Run natively on the tablet: compare immutable userspace to its RAM source.

Outputs counts/differences only, never credentials or file contents.
"""
import hashlib
import os
from pathlib import Path
import stat

source = Path('/')
target = Path('/mnt/t630-install')
count = 0
differences = []
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.digest()

for directory in ['usr', 'opt']:
    for base, dirs, files in os.walk(source / directory, followlinks=False):
        for name in dirs + files:
            original = Path(base) / name
            relative = original.relative_to(source)
            # These two intentionally advance from the saved v3 to running v4.
            if str(relative) in ['usr/local/lib/t630-drm-compat.so', 'opt/t630/t630-drm-compat.c']:
                continue
            copied = target / relative
            a = original.lstat()
            try:
                b = copied.lstat()
                assert (a.st_mode, a.st_uid, a.st_gid) == (b.st_mode, b.st_uid, b.st_gid)
                if stat.S_ISREG(a.st_mode):
                    assert a.st_size == b.st_size and digest(original) == digest(copied)
                elif stat.S_ISLNK(a.st_mode):
                    assert os.readlink(original) == os.readlink(copied)
            except (OSError, AssertionError):
                differences.append(str(relative))
            count += 1
print(f'Compared {count} userspace entries; differences: {len(differences)}')
for path in differences[:30]:
    print(path)
raise SystemExit(bool(differences))
