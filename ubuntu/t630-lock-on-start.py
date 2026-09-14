#!/usr/bin/python3
"""Request and verify GNOME's password lock once its session bus is ready.

This is a startup desktop lock, not a display-manager greeter or a replacement
for the lab recovery security boundary. No passwords are handled here.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner
assert os.getuid() == resolve_owner().uid


def call(bus, dest, path, method, *args, timeout=2):
    try:
        result = subprocess.run(['gdbus', 'call', bus, '--dest', dest,
                                 '--object-path', path, '--method', method, *args],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None


screen = ('--session', 'org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
deadline = time.monotonic() + 40
while time.monotonic() < deadline:
    active = call(*screen, 'org.gnome.ScreenSaver.GetActive')
    locked = call('--system', 'org.freedesktop.login1',
                  '/org/freedesktop/login1/session/self',
                  'org.freedesktop.DBus.Properties.Get',
                  'org.freedesktop.login1.Session', 'LockedHint')
    if active == '(true,)' and locked == '(<true>,)':
        print('GNOME startup password lock verified. Lab recovery remains separate.', flush=True)
        raise SystemExit(0)
    if active is not None:
        call(*screen, 'org.gnome.ScreenSaver.Lock', timeout=5)
    time.sleep(.25)
print('Startup password lock did not verify; refusing to finish desktop startup.', flush=True)
raise SystemExit(1)
