#!/usr/bin/python3
"""Launch a normal-user app in the existing tablet GNOME session.

Read only the selected session environment; never print it. This helper is
not setuid and provides no authorization bypass or elevated app execution.
"""
import os
from pathlib import Path
import re
import sys

if os.getuid() not in (0, 1000) or len(sys.argv) < 2:
    raise SystemExit('Usage: t630-gnome-run COMMAND [ARGS...]')
sessions = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != 1000:
            continue
        if os.readlink(proc / 'exe') != '/usr/bin/gnome-shell':
            continue
        values = dict(item.split(b'=', 1) for item in
                      (proc / 'environ').read_bytes().split(b'\0') if b'=' in item)
        if values.get(b'XDG_CONFIG_HOME') == b'/home/tablet/.config/t630-gnome-preview':
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
env.update(HOME='/home/tablet', USER='tablet', LOGNAME='tablet',
           PATH='/usr/local/bin:/usr/bin:/bin', LANG='C.UTF-8',
           WAYLAND_DISPLAY='t630-gnome-0', XDG_SESSION_TYPE='wayland',
           XDG_CURRENT_DESKTOP='GNOME', GDK_BACKEND='wayland',
           GSK_RENDERER='cairo', LIBGL_ALWAYS_SOFTWARE='1',
           GALLIUM_DRIVER='llvmpipe', MOZ_ENABLE_WAYLAND='1')
if os.getuid() == 0:
    # Root SSH/audio launchers must join the actual desktop's session before
    # dropping privileges, so login1 sees these apps as the same tablet user.
    for entry in (session_proc / 'cgroup').read_text().splitlines():
        _, controllers, group_path = entry.split(':', 2)
        if controllers == 'name=elogind' and re.fullmatch(r'/c[0-9]+', group_path):
            target = Path('/sys/fs/cgroup/elogind') / group_path[1:] / 'cgroup.procs'
            with target.open('w') as stream:
                stream.write(str(os.getpid()))
            break
    os.initgroups('tablet', 1000)
    os.setgid(1000)
    os.setuid(1000)
os.chdir('/home/tablet')
os.execvpe(sys.argv[1], sys.argv[1:], env)
