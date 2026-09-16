#!/usr/bin/python3
"""Seed tablet-safe Xournal++ defaults once for the current desktop owner."""

import os
from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET


MAX_SETTINGS_BYTES = 2 * 1024 * 1024
MARKER_NAME = 'xournalpp-palm-default-v1'
TOUCH_BLOCK = (
    '  <data name="touch">\n'
    '    <attribute name="disableTouch" type="boolean" value="true"/>\n'
    '    <attribute name="method" type="string" value="auto"/>\n'
    '    <attribute name="timeout" type="int" value="1000"/>\n'
    '  </data>\n'
)


def _regular_owned(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Refusing non-regular path: {path}')
    if path.stat().st_uid != os.getuid():
        raise ValueError(f'Refusing settings not owned by the desktop user: {path}')


def _write_atomic(path, data, mode):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _patched_settings(original):
    if len(original) > MAX_SETTINGS_BYTES:
        raise ValueError('Xournal++ settings are unexpectedly large')
    root = ET.fromstring(original)
    if root.tag != 'settings':
        raise ValueError('Unexpected Xournal++ settings root')
    touch = next((item for item in root.findall('data') if item.get('name') == 'touch'), None)
    if touch is not None and any(item.get('name') == 'disableTouch' for item in touch.findall('attribute')):
        return None

    text = original.decode('utf-8')
    empty = '  <data name="touch"/>\n'
    opening = '  <data name="touch">\n'
    if touch is not None and text.count(empty) == 1:
        updated = text.replace(empty, TOUCH_BLOCK, 1)
    elif touch is not None and text.count(opening) == 1:
        attributes = TOUCH_BLOCK[len(opening):-len('  </data>\n')]
        updated = text.replace(opening, opening + attributes, 1)
    elif touch is None and text.count('</settings>') == 1:
        updated = text.replace('</settings>', TOUCH_BLOCK + '</settings>', 1)
    else:
        raise ValueError('Cannot safely place the Xournal++ palm-rejection default')
    encoded = updated.encode('utf-8')
    checked = ET.fromstring(encoded)
    configured = next(item for item in checked.findall('data') if item.get('name') == 'touch')
    values = {item.get('name'): item.get('value') for item in configured.findall('attribute')}
    if values.get('disableTouch') != 'true' or values.get('method') != 'auto' or values.get('timeout') != '1000':
        raise ValueError('Palm-rejection settings did not validate')
    return encoded


def seed_palm_rejection(config_home, state_home):
    settings = Path(config_home) / 'xournalpp' / 'settings.xml'
    marker = Path(state_home) / 't630' / MARKER_NAME
    if marker.exists():
        _regular_owned(marker)
        return 'already-seeded'

    if settings.exists():
        _regular_owned(settings)
        original = settings.read_bytes()
        updated = _patched_settings(original)
        if updated is not None:
            backup = settings.with_name(f'{settings.name}.before-t630-palm-default')
            if not backup.exists():
                shutil.copy2(settings, backup, follow_symlinks=False)
            _write_atomic(settings, updated, settings.stat().st_mode & 0o777)
            result = 'enabled'
        else:
            result = 'existing-choice-preserved'
    else:
        initial = ('<?xml version="1.0" encoding="UTF-8"?>\n<settings>\n' +
                   TOUCH_BLOCK + '</settings>\n').encode('utf-8')
        ET.fromstring(initial)
        _write_atomic(settings, initial, 0o600)
        result = 'enabled'

    _write_atomic(marker, b'Xournal++ internal hand recognition default seeded once.\n', 0o600)
    return result


def main():
    if os.getuid() == 0:
        raise SystemExit('Run as the normal desktop owner, not root.')
    home = Path(os.environ.get('HOME', ''))
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    state_home = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    if not home.is_absolute() or not config_home.is_absolute() or not state_home.is_absolute():
        raise SystemExit('HOME and XDG paths must be absolute.')
    try:
        seed_palm_rejection(config_home, state_home)
    except (OSError, ValueError, ET.ParseError) as error:
        print(f't630-xournalpp-defaults: preserving existing settings: {error}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
