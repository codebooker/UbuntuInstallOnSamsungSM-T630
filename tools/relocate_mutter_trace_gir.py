#!/usr/bin/env python3
"""Emit a private GIR with its exact library pinned to the RAM trace bundle.

Avoid GI loading the distro library alongside the diagnostic library. Does not
edit input GIRs, system typelibs, namespaces, versions, or API declarations.
"""
import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from prepare_mutter_trace_session import DIRECTORY


LIBRARIES = {
    'Cogl': 'libmutter-cogl-14.so.0',
    'CoglPango': 'libmutter-cogl-pango-14.so.0',
    'Clutter': 'libmutter-clutter-14.so.0',
    'Cally': 'libmutter-clutter-14.so.0',
    'Meta': 'libmutter-14.so.0',
    'Mtk': 'libmutter-mtk-14.so.0',
}


def relocate(text):
    root = ET.fromstring(text)
    namespaces = root.findall('{http://www.gtk.org/introspection/core/1.0}namespace')
    if len(namespaces) != 1:
        raise ValueError('Require one reviewed Mutter namespace.')
    namespace = namespaces[0]
    expected = LIBRARIES.get(namespace.get('name'))
    if not expected or namespace.get('version') != '14':
        raise ValueError('Unreviewed namespace/version.')
    if namespace.get('shared-library') != expected:
        raise ValueError('Unexpected shared library; refusing arbitrary paths.')
    anchor = f'shared-library="{expected}"'
    if text.count(anchor) != 1:
        raise ValueError('Ambiguous shared-library declaration.')
    return text.replace(anchor, f'shared-library="{DIRECTORY}/{expected}"')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gir', type=Path)
    args = parser.parse_args()
    sys.stdout.write(relocate(args.gir.read_text()))


if __name__ == '__main__':
    main()
