#!/usr/bin/python3
"""Bounded root-only session-accounting test for the existing lab desktop.

This is not password authentication and must not be used as a login verifier.
It registers the already-running UID1000 GNOME with the real login1 service.
"""
import os
from pathlib import Path
import time
from gi.repository import Gio, GLib

if os.getuid() != 0 or Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
    raise SystemExit('Run only as root on the validated lab installation.')
shells = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid == 1000 and os.readlink(proc / 'exe') == '/usr/bin/gnome-shell':
            shells.append(int(proc.name))
    except OSError:
        pass
if len(shells) != 1:
    raise SystemExit('Expected exactly one normal-user GNOME.')
bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
result, fds = bus.call_with_unix_fd_list_sync(
    'org.freedesktop.login1', '/org/freedesktop/login1',
    'org.freedesktop.login1.Manager', 'CreateSession',
    GLib.Variant('(uusssssussbssa(sv))',
                 (1000, shells[0], 't630-lab-session', 'wayland', 'user',
                  'GNOME', '', 0, '', '', False, '', '', [])),
    None, Gio.DBusCallFlags.NONE, 15000, None, None)
info = result.unpack()
fd = fds.get(info[3])
print(f'Registered GNOME pid={shells[0]} session={info[0]} path={info[1]}', flush=True)
try:
    # Bounded test holder, not an installed startup service.
    for _ in range(600):
        if not Path(f'/proc/{shells[0]}').exists():
            break
        time.sleep(1)
finally:
    os.close(fd)
