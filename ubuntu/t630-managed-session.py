#!/usr/bin/python3
"""Account for the existing auto-start lab session with the real login1 service.

Root-only launcher, NOT a password verifier. GDM/PAM handle screen unlock.
The child is registered before it creates any normal-user runtime sockets.
"""
import os
from pathlib import Path
import signal
import sys
from gi.repository import Gio, GLib

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner

if os.getuid() != 0 or Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
    raise SystemExit('Only for the validated root desktop launcher.')
if sys.argv[1:] != ['/usr/local/bin/t630-gnome-preview']:
    raise SystemExit('Only the installed GNOME launcher is accepted.')
owner = resolve_owner()
reader, writer = os.pipe()
pid = os.fork()
if pid == 0:
    # Give this exact desktop tree its own process group. A wrapper stop can
    # then reach dbus-run-session and every descendant without touching Weston
    # or unrelated tablet services.
    os.setsid()
    os.close(writer)
    session = os.read(reader, 128).decode().strip()
    os.close(reader)
    if not session:
        os._exit(1)
    os.environ['XDG_SESSION_ID'] = session
    os.environ['T630_LOGIN_SESSION_WRAPPED'] = '1'
    os.execv(sys.argv[1], sys.argv[1:])
os.close(reader)
fd = None
try:
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    reply, fds = bus.call_with_unix_fd_list_sync(
        'org.freedesktop.login1', '/org/freedesktop/login1',
        'org.freedesktop.login1.Manager', 'CreateSession',
        GLib.Variant('(uusssssussbssa(sv))',
                     (owner.uid, pid, 't630-session', 'wayland', 'user',
                      'GNOME', '', 0, '', '', False, '', '', [])),
        None, Gio.DBusCallFlags.NONE, 15000, None, None)
    info = reply.unpack()
    fd = fds.get(info[3])
    os.write(writer, info[0].encode())
    os.close(writer)
    writer = None
    print(f'GNOME session {info[0]} registered before startup.', flush=True)

    def stop_child(_signal, _frame):
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    # The shell that becomes this wrapper has already started a few root-side
    # tablet services. They remain our direct children across exec(). Reap
    # completed one-shot helpers while continuing to wait for the exact GNOME
    # child; otherwise every desktop start leaves zombies for the life of the
    # boot.
    status = None
    while status is None:
        reaped_pid, reaped_status = os.waitpid(-1, 0)
        if reaped_pid == pid:
            status = reaped_status
    sys.exit(os.waitstatus_to_exitcode(status))
finally:
    if writer is not None:
        os.close(writer)
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
    if fd is not None:
        os.close(fd)
