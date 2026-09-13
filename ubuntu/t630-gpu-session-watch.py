#!/usr/bin/python3
"""Bound GPU GNOME startup and later hangs; own normal-user child only.

No unlock method, credentials, kernel reset, or unrelated process signaling.
The existing parent launcher decides whether to retry using software rendering.
"""
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def bus_call(destination, path, method, *args):
    try:
        result = subprocess.run(
            ['gdbus', 'call', '--session', '--dest', destination,
             '--object-path', path, '--method', method, *args],
            capture_output=True, text=True, timeout=2, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def desktop_ready(pid):
    owner = bus_call('org.freedesktop.DBus', '/org/freedesktop/DBus',
                     'org.freedesktop.DBus.GetConnectionUnixProcessID',
                     'org.gnome.Shell')
    match = re.fullmatch(r'\(uint32 ([0-9]+),\)', owner or '')
    if not match or int(match.group(1)) != pid:
        return False
    return bus_call('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver',
                    'org.gnome.ScreenSaver.GetActive') in ('(true,)', '(false,)')


def stop_owned_child(child, grace=5):
    # Popen retains ownership and reaps the exact child, avoiding PID searches.
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=3)


def supervise(command, ready=desktop_ready, startup_timeout=45, stop_grace=5,
              health_interval=5, health_failures=3):
    child = subprocess.Popen(command)
    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    old_handlers = {sig: signal.signal(sig, request_stop)
                    for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        deadline = time.monotonic() + startup_timeout
        while child.poll() is None and not stopping:
            if ready(child.pid):
                print('GPU GNOME startup bus check passed; stability is not guaranteed.',
                      flush=True)
                break
            if time.monotonic() >= deadline:
                print('GPU GNOME startup did not respond; stopping owned child for fallback.',
                      flush=True)
                return 1
            time.sleep(0.25)
        else:
            return 143 if stopping else (child.returncode or 1)

        failures = 0
        next_health = time.monotonic() + health_interval
        while child.poll() is None and not stopping:
            if time.monotonic() >= next_health:
                if ready(child.pid):
                    failures = 0
                else:
                    failures += 1
                if failures >= health_failures:
                    print('GPU GNOME stopped responding; stopping owned child for software fallback.',
                          flush=True)
                    return 1
                next_health = time.monotonic() + health_interval
            time.sleep(0.25)
        return 143 if stopping else child.returncode
    finally:
        stop_owned_child(child, grace=stop_grace)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)


def main():
    if os.getuid() != 1000:
        raise SystemExit('GPU session watcher must run as the tablet user.')
    if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
        raise SystemExit('Unexpected tablet installation.')
    command = sys.argv[1:]
    if command[:2] != ['/usr/local/bin/t630-gpu-env', '/usr/bin/gnome-shell']:
        raise SystemExit('Expected the scoped GPU GNOME command.')
    raise SystemExit(supervise(command))


if __name__ == '__main__':
    main()
