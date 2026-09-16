#!/usr/bin/env python3
"""Generate a manual RAM-only session for a hashed diagnostic Mutter build.

Does not install, launch, change defaults, or bypass startup authentication.
No proximity preload is used. The normal session remains the recovery path.
"""
import argparse
import json
from pathlib import Path
import re

from prepare_pen_session_trial import prepare


DIRECTORY = '/run/t630-mutter-pen-trace-20260915'
LIBRARIES = (
    'libmutter-14.so.0',
    'libmutter-clutter-14.so.0',
    'libmutter-cogl-14.so.0',
    'libmutter-cogl-pango-14.so.0',
    'libmutter-mtk-14.so.0',
)
TYPELIBS = tuple('typelibs/' + name + '-14.typelib'
                for name in ('Cogl', 'CoglPango', 'Clutter', 'Cally', 'Meta', 'Mtk'))
ARTIFACTS = LIBRARIES + TYPELIBS


def generate(base, hashes, source_trial=False):
    if set(hashes) != set(ARTIFACTS):
        raise ValueError('Require the five libraries and six matching private typelibs.')
    if any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
           for value in hashes.values()):
        raise ValueError('Invalid diagnostic library SHA-256.')
    text = prepare(base, proximity=False).decode()
    anchor = 'export LD_PRELOAD=/usr/local/lib/t630-cogl-sync.so\n'
    if text.count(anchor) != 1:
        raise ValueError('Unknown diagnostic renderer insertion point.')
    gate = '''# Manual source-build diagnostic: fail closed, never a default.
test "${T630_MUTTER_PEN_TRACE:-0}" = 1
test "${T630_PEN_METADATA_TRIAL:-0}" = 1
'''
    if source_trial:
        gate += '''# Unaccepted real-event handoff trial; physical hover-out remains pending.
test "${T630_X11_PEN_FIX:-0}" = 1
export T630_X11_PEN_FIX
'''
    for library in ARTIFACTS:
        gate += f'''test "$(sha256sum {DIRECTORY}/{library} | cut -d ' ' -f 1)" = {hashes[library]}
'''
    gate += f'''export LD_LIBRARY_PATH={DIRECTORY}
export GI_TYPELIB_PATH={DIRECTORY}/typelibs
'''
    return text.replace(anchor, anchor + gate).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-trial', action='store_true',
                        help='Require the additional explicit real-event handoff flag.')
    args = parser.parse_args()
    result = generate(args.base.read_bytes(), json.loads(args.manifest.read_text()),
                      source_trial=args.source_trial)
    with args.output.open('xb') as output:
        output.write(result)
    print('Manual diagnostic generated; normal startup remains unchanged.')


if __name__ == '__main__':
    main()
