#!/usr/bin/python3
"""Quarantine this project's stale X3 socket after an unclean shutdown."""
import os
from pathlib import Path
import stat

assert os.getuid() == 0
socket_path = Path('/tmp/.X11-unix/X3')
lock_path = Path('/tmp/.X3-lock')
active = {line.split()[-1] for line in Path('/proc/net/unix').read_text().splitlines()[1:]
          if len(line.split()) >= 8}
if str(socket_path) in active or '@' + str(socket_path) in active:
    raise SystemExit('X3 is still in use; refusing to move its socket or lock.')
stale = []
for path in (socket_path, lock_path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        continue
    assert info.st_uid == 1000 and not stat.S_ISLNK(info.st_mode)
    assert stat.S_ISSOCK(info.st_mode) if path == socket_path else stat.S_ISREG(info.st_mode)
    stale.append(path)
if stale:
    import tempfile
    base = Path('/var/lib/t630/stale-x11')
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='X3-', dir=base))
    for path in stale:
        path.rename(destination / path.name)
    print('Quarantined stale X3 startup files; no running X server was touched.')
