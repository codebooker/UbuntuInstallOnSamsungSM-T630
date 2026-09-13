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

if os.getuid() != 0 or Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
    raise SystemExit('Only for the validated root desktop launcher.')
if sys.argv[1:] != ['/usr/local/bin/t630-gnome-preview']:
    raise SystemExit('Only the installed GNOME launcher is accepted.')
reader, writer = os.pipe()
pid = os.fork()
if pid == 0:
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
                     (1000, pid, 't630-lab-session', 'wayland', 'user',
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
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    _, status = os.waitpid(pid, 0)
    sys.exit(os.waitstatus_to_exitcode(status))
finally:
    if writer is not None:
        os.close(writer)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
    if fd is not None:
        os.close(fd)
