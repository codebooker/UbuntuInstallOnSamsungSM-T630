#!/usr/bin/env python3
"""Generate a hash-gated, manual RAM-session experiment; never install it."""
import argparse
import hashlib
from pathlib import Path

# Reviewed after adding the owner-scoped Chrome editable-focus OSK bridge and
# its late-install launcher watcher. The pressure trial remains opt-in.
BASE_SHA = '02f9aec44db2ea7b7784eb3db6086c3e603ae58210d9fef7a258f8ba15e31791'
PREPARE = '''if [ "${T630_PEN_METADATA_TRIAL:-0}" = 1 ]; then
    /usr/bin/python3 /usr/local/libexec/t630-pen-x11-metadata --prepare
fi
'''
PUBLISH = '''if [ "${T630_PEN_METADATA_TRIAL:-0}" = 1 ]; then
    /usr/bin/python3 /usr/local/libexec/t630-pen-x11-metadata --publish-tool
fi
'''
BRIDGE = '''if [ "${T630_PEN_PROXIMITY_TRIAL:-0}" = 1 ]; then
    test "${T630_PEN_METADATA_TRIAL:-0}" = 1
    test -r /run/t630-pen-floating-trial.so
    test "$(sha256sum /usr/lib/aarch64-linux-gnu/libmutter-14.so.0 | cut -d ' ' -f 1)" = \\
        94d5c4d40ff84a90ad2533adc69671c182ac2e11799c15f3a9dcbcc5b61b0af6
    test "$(sha256sum /usr/lib/aarch64-linux-gnu/mutter-14/libmutter-clutter-14.so.0 | cut -d ' ' -f 1)" = \\
        541366ce84e2a6454d0ec94cf040951e815a157af368ac5344d6f802643c482e
    test "$(sha256sum /run/t630-pen-floating-trial.so | cut -d ' ' -f 1)" = \\
        25d46009dea13f632b42c7e346d05a846abe7116e2aea1c3543b5f4c72350b40
    export LD_PRELOAD=/run/t630-pen-floating-trial.so:$LD_PRELOAD
fi
'''


def prepare(source, proximity=False):
    if hashlib.sha256(source).hexdigest() != BASE_SHA:
        raise ValueError('Unknown base session; review the experiment before using a new build.')
    text = source.decode()
    for anchor, fragment in (
        ('if [ -x /usr/local/libexec/t630-auth-watch ]; then\n', PREPARE),
        ('if [ -x /usr/libexec/gsd-media-keys ]; then\n', PUBLISH),
    ):
        if text.count(anchor) != 1:
            raise ValueError('Ambiguous session insertion point.')
        text = text.replace(anchor, fragment + anchor)
    if proximity:
        anchor = 'export LD_PRELOAD=/usr/local/lib/t630-cogl-sync.so\n'
        if text.count(anchor) != 1:
            raise ValueError('Ambiguous renderer insertion point.')
        text = text.replace(anchor, anchor + BRIDGE)
    return text.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--proximity', action='store_true')
    args = parser.parse_args()
    result = prepare(args.base.read_bytes(), args.proximity)
    # New artifact only: no modification of the base session or installed files.
    with args.output.open('xb') as target:
        target.write(result)
    print('Generated manual trial; startup remains opt-in, pressure is not accepted.')


if __name__ == '__main__':
    main()
