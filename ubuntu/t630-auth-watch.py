#!/usr/bin/python3
"""Attach native password dialogs to selected same-user desktop processes.

No authorization policy is changed. Polkit/PAM still verify passwords.
This provides process-scoped agents until a real login session is available.
"""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import time
from gi.repository import Gio, GLib

import sys
sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner

owner = resolve_owner()
assert os.getuid() == owner.uid
runtime = Path('/run/user') / str(owner.uid)
lock = open(runtime / 't630-auth-watch.lock', 'w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)

helper = '/usr/local/libexec/t630-polkit-agent'
allowed = {'/usr/bin/gnome-software', '/usr/bin/gnome-control-center',
           '/usr/bin/nautilus', '/usr/bin/gnome-disks'}
bus = os.environ['DBUS_SESSION_BUS_ADDRESS'].split(',')[0]
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
connection.set_exit_on_close(False)
children = {}
running = True

def stop(*_):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while running:
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(False)
        if connection.is_closed():
            break
        candidates = {}
        active_targets = set()
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if proc.stat().st_uid != owner.uid:
                    continue
                executable = os.readlink(proc / 'exe')
                if executable in (helper, helper + ' (deleted)'):
                    args = (proc / 'cmdline').read_bytes().split(b'\0')
                    if len(args) > 1 and args[1].isdigit():
                        active_targets.add(int(args[1]))
                    continue
                if executable not in allowed:
                    continue
                values = dict(item.split(b'=', 1) for item in
                              (proc / 'environ').read_bytes().split(b'\0')
                              if b'=' in item)
                address = values.get(b'DBUS_SESSION_BUS_ADDRESS', b'').decode()
                if address.split(',')[0] != bus:
                    continue
                if values.get(b'WAYLAND_DISPLAY') != b't630-gnome-0':
                    continue
                candidates[int(proc.name)] = values
            except (OSError, ValueError):
                continue
        for pid, child in list(children.items()):
            status = child.poll()
            if status is not None:
                print(f'Authentication dialog for process {pid} exited: {status}',
                      flush=True)
                del children[pid]
        for pid, values in candidates.items():
            if pid in active_targets or pid in children:
                continue
            env = {key: value.decode() for key, value in
                   ((name, values[name.encode()]) for name in
                    ('HOME', 'XDG_RUNTIME_DIR', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME',
                     'XDG_CACHE_HOME', 'DBUS_SESSION_BUS_ADDRESS', 'WAYLAND_DISPLAY')
                    if name.encode() in values)}
            env.update(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C.UTF-8',
                       GDK_BACKEND='wayland', GTK_IM_MODULE='wayland',
                       GTK_THEME='Adwaita:dark')
            children[pid] = subprocess.Popen([helper, str(pid)], env=env,
                cwd=owner.home, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
finally:
    for child in children.values():
        if child.poll() is None:
            child.terminate()
