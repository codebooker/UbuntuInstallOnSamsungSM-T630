#!/usr/bin/python3
"""Stop only stale audio servers belonging to the exact tablet desktop profile.

Root startup repair after the normal audio socket stops responding. No kernel
module changes, device controls, passwords, or unrelated process signaling.
"""
import os
from pathlib import Path
import select
import signal
import sys
import time

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner


def matches(uid, executable, name, env, owner):
    expected_config = f'{owner.home}/.config/t630-gnome-preview'.encode()
    expected_runtime = f'/run/user/{owner.uid}'.encode()
    return (uid == owner.uid and name in ('pipewire', 'pipewire-pulse', 'wireplumber')
            and executable in ('/usr/bin/pipewire', '/usr/bin/pipewire-pulse', '/usr/bin/wireplumber')
            and env.get(b'XDG_CONFIG_HOME') == expected_config
            and env.get(b'XDG_RUNTIME_DIR') == expected_runtime)


def main():
    assert os.geteuid() == 0
    assert Path('/etc/t630-install-id').read_text().strip() == 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
    owner = resolve_owner()
    handles = []
    try:
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if proc.stat().st_uid != owner.uid:
                    continue
                name = (proc / 'comm').read_text().strip()
                if name not in ('pipewire', 'pipewire-pulse', 'wireplumber'):
                    continue
                handle = os.pidfd_open(int(proc.name))
                handles.append(handle)
                env = dict(item.split(b'=', 1) for item in (proc / 'environ').read_bytes().split(b'\0')
                           if b'=' in item)
                if not matches(proc.stat().st_uid, os.readlink(proc / 'exe'), name, env, owner):
                    os.close(handles.pop())
                    continue
                signal.pidfd_send_signal(handle, signal.SIGTERM)
                print('Stopped stale tablet audio server: ' + name, flush=True)
            except (FileNotFoundError, ProcessLookupError):
                continue
        deadline = time.monotonic() + 5
        pending = list(handles)
        while pending and time.monotonic() < deadline:
            finished, _, _ = select.select(pending, [], [], max(0, deadline - time.monotonic()))
            pending = [handle for handle in pending if handle not in finished]
        if pending:
            raise RuntimeError('An old audio server did not stop; refusing duplicate startup')
    finally:
        for handle in handles:
            os.close(handle)


if __name__ == '__main__':
    main()
