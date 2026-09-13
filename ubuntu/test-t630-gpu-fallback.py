#!/usr/bin/python3
"""Freeze one validated, locked GPU GNOME child to test its watchdog.

If it is not stopped by the watchdog within45seconds, resume that exact pidfd.
No reboot, driver reset, authentication bypass, or unrelated process signals.
"""
import os
from pathlib import Path
import select
import signal
import subprocess
import sys

assert os.geteuid() == 0
assert len(sys.argv) == 2 and sys.argv[1].isdigit()
assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
pid = int(sys.argv[1])
fd = os.pidfd_open(pid)
def interrupted(_signal, _frame):
    raise SystemExit(143)
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGHUP, interrupted)
try:
    proc = Path('/proc') / str(pid)
    assert proc.stat().st_uid == 1000
    assert os.readlink(proc / 'exe') == '/usr/bin/gnome-shell'
    assert b'--wayland-display=t630-gnome-0' in (proc / 'cmdline').read_bytes().split(b'\0')
    assert '/opt/t630/mesa-25.2.8-kgsl/' in (proc / 'maps').read_text()
    assert Path('/etc/t630/gpu.disabled').exists()
    assert subprocess.check_output([
        '/usr/local/bin/t630-gnome-run', 'gdbus', 'call', '--session',
        '--dest', 'org.gnome.ScreenSaver', '--object-path', '/org/gnome/ScreenSaver',
        '--method', 'org.gnome.ScreenSaver.GetActive'], text=True, timeout=8).strip() == '(true,)'
    signal.pidfd_send_signal(fd, signal.SIGSTOP)
    print('Paused the exact GPU GNOME child;45-second resume safety net armed.', flush=True)
    exited, _, _ = select.select([fd], [], [], 45)
    if exited:
        print('Watchdog terminated the paused child; verify software fallback separately.', flush=True)
    else:
        signal.pidfd_send_signal(fd, signal.SIGCONT)
        raise RuntimeError('Watchdog did not terminate the child; resumed it safely')
finally:
    # Cover interruption/errors without ever signaling a recycled process ID.
    try:
        signal.pidfd_send_signal(fd, signal.SIGCONT)
    except ProcessLookupError:
        pass
    os.close(fd)
