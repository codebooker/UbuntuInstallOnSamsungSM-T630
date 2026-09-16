#!/usr/bin/python3
"""Set MyPaint's normal owner preference to a lighter, zero-preserving curve.

Close MyPaint normally first. This changes only its global pressure preference,
backs up existing settings, and preserves other settings. No device or kernel
changes, event injection, handwriting recording, or root app execution.
"""
import argparse
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


KEY = 'input.global_pressure_mapping'


def curve(full_pressure):
    if isinstance(full_pressure, bool) or not isinstance(full_pressure, (int, float)):
        raise ValueError('Full-pressure threshold must be numeric.')
    if not math.isfinite(full_pressure) or not 0.2 <= full_pressure <= 1.0:
        raise ValueError('Use a full-pressure threshold from 0.2 to 1.0.')
    # MyPaint stores its graph Y inverted, and applies (1 - y) to pressure.
    # Preserve zero so hovering never becomes painting. 1.0 restores identity.
    if full_pressure == 1.0:
        return [[0.0, 1.0], [1.0, 0.0]]
    return [[0.0, 1.0], [float(full_pressure), 0.0], [1.0, 0.0]]


def running_mypaint(proc_root=Path('/proc')):
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
            if any(arg in (b'/usr/bin/mypaint', b'/usr/local/libexec/t630-mypaint')
                   or arg.endswith((b'/probe_mypaint_latency.py', b'/probe_mypaint_latency_v2.py'))
                   for arg in argv):
                return True
        except FileNotFoundError:
            continue
        except PermissionError:
            # Don't modify a live app's settings if same-owner inspection fails.
            raise RuntimeError('Cannot safely inspect owner processes.')
    return False


def configure(path, full_pressure):
    points = curve(full_pressure)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError('Refusing symlinked MyPaint settings.')
    preferences = {}
    previous = None
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 2**20:
            raise ValueError('Unexpected MyPaint settings file.')
        previous = path.read_bytes()
        preferences = json.loads(previous)
        if not isinstance(preferences, dict):
            raise ValueError('Expected a MyPaint preferences object.')
    preferences[KEY] = points
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.stat().st_uid != os.getuid():
        raise ValueError('Settings directory is not owned by the desktop user.')
    backup = None
    if previous is not None:
        fd, name = tempfile.mkstemp(prefix='settings-before-pen-sensitivity-',
                                    suffix='.json', dir=path.parent)
        backup = Path(name)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(previous)
            stream.flush()
            os.fsync(stream.fileno())
    fd, name = tempfile.mkstemp(prefix='.settings-pressure-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(preferences, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-pressure', type=float, default=1.0,
                        help='Raw pressure reaching full brush response (0.2–1.0; default 1.0 restores identity).')
    args = parser.parse_args()
    curve(args.full_pressure)
    sys.path.insert(0, '/usr/local/share/t630')
    from t630_account import resolve_owner
    owner = resolve_owner()
    expected = str(Path(owner.home) / '.config/t630-gnome-preview')
    if os.getuid() == 0 or os.getuid() != owner.uid or os.environ.get('XDG_CONFIG_HOME') != expected:
        raise SystemExit('Run as the owner through the existing t630-gnome-run helper.')
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W', '-f=${Version}',
                                       'mypaint'], text=True).strip()
    if version != '2.0.1-10build2':
        raise SystemExit('Review pressure preference semantics before using another MyPaint version.')
    if running_mypaint():
        raise SystemExit('Close MyPaint normally first; no settings changed.')
    backup = configure(Path(expected) / 'mypaint/settings.json', args.full_pressure)
    print(f'MyPaint pressure curve set: full response at {args.full_pressure:.0%} raw pressure.')
    print('Hover remains zero; other preferences retained. Reopen MyPaint.')
    if backup is not None:
        print('Previous settings backed up alongside settings.json.')


if __name__ == '__main__':
    main()
