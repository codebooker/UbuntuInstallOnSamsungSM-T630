#!/usr/bin/python3
"""Launch a normal-user app in the existing tablet GNOME session.

Read only the selected session environment; never print it. This helper is
not setuid and provides no authorization bypass or elevated app execution.
"""
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_locale, resolve_owner

owner = resolve_owner()
if os.getuid() not in (0, owner.uid) or len(sys.argv) < 2:
    raise SystemExit('Usage: t630-gnome-run COMMAND [ARGS...]')
sessions = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != owner.uid:
            continue
        if os.readlink(proc / 'exe') != '/usr/bin/gnome-shell':
            continue
        values = dict(item.split(b'=', 1) for item in
                      (proc / 'environ').read_bytes().split(b'\0') if b'=' in item)
        expected = f'{owner.home}/.config/t630-gnome-preview'.encode()
        if values.get(b'XDG_CONFIG_HOME') == expected:
            sessions.append((proc, values))
    except (OSError, ValueError):
        continue
if len(sessions) != 1:
    raise SystemExit('Expected exactly one running tablet GNOME session.')
session_proc, values = sessions[0]
env = {name: values[name.encode()].decode() for name in
       ('DBUS_SESSION_BUS_ADDRESS', 'XAUTHORITY', 'XDG_RUNTIME_DIR', 'XDG_SESSION_ID',
        'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME')
       if name.encode() in values}
env.update(HOME=owner.home, USER=owner.username, LOGNAME=owner.username,
           PATH='/usr/local/bin:/usr/bin:/bin', LANG=resolve_locale(),
           WAYLAND_DISPLAY='t630-gnome-0', XDG_SESSION_TYPE='wayland',
           XDG_CURRENT_DESKTOP='GNOME', GDK_BACKEND='wayland',
           GSK_RENDERER='cairo', LIBGL_ALWAYS_SOFTWARE='1',
           GALLIUM_DRIVER='llvmpipe', MOZ_ENABLE_WAYLAND='1')
if os.getuid() == 0:
    # Root SSH/audio launchers must join the actual desktop's session before
    # dropping privileges, so login1 sees these apps as the same tablet user.
    for entry in (session_proc / 'cgroup').read_text().splitlines():
        _, controllers, group_path = entry.split(':', 2)
        # systemd-logind commonly names these /cNN; elogind may use /NN after
        # recreating the same custom session. In either case, accept only the
        # numeric session cgroup reported by the selected GNOME process.
        if controllers == 'name=elogind' and re.fullmatch(r'/c?[0-9]+', group_path):
            target = Path('/sys/fs/cgroup/elogind') / group_path[1:] / 'cgroup.procs'
            with target.open('w') as stream:
                stream.write(str(os.getpid()))
            break
    os.initgroups(owner.username, owner.gid)
    os.setgid(owner.gid)
    os.setuid(owner.uid)
os.chdir(owner.home)
os.execvpe(sys.argv[1], sys.argv[1:], env)
