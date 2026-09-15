#!/usr/bin/python3
"""Keep stock utilities individually accessible; preserve personal app folders.

An empty folder list causes Shell to create its defaults again. A reserved,
empty (invisible) folder suppresses that initialization without patching Shell.
"""
import os
import sys

SENTINEL = 't630-flat-layout'
DEFAULT_FOLDERS = {'Utilities', 'YaST', 'Pardus'}
DEFAULT_FAVORITES = ['firefox.desktop', 'org.gnome.Nautilus.desktop',
                     'org.gnome.Software.desktop', 'org.gnome.TextEditor.desktop',
                     'org.gnome.Terminal.desktop', 'org.gnome.Settings.desktop']


def apply(settings_factory, pin_drawing=False):
    folders = settings_factory(schema_id='org.gnome.desktop.app-folders')
    empty = settings_factory(schema_id='org.gnome.desktop.app-folders.folder',
        path=f'/org/gnome/desktop/app-folders/folders/{SENTINEL}/')
    empty.set_string('name', 'Apps')
    empty.set_boolean('translate', False)
    for key in ('apps', 'categories', 'excluded-apps'):
        empty.set_strv(key, [])
    children = [item for item in folders.get_strv('folder-children')
                if item not in DEFAULT_FOLDERS and item != SENTINEL]
    folders.set_strv('folder-children', children + [SENTINEL])
    shell = settings_factory(schema_id='org.gnome.shell')
    if shell.get_user_value('favorite-apps') is None:
        shell.set_strv('favorite-apps', DEFAULT_FAVORITES)
    if pin_drawing:
        favorites = shell.get_strv('favorite-apps')
        if 'mypaint.desktop' not in favorites:
            shell.set_strv('favorite-apps', favorites + ['mypaint.desktop'])


def main():
    if os.getuid() == 0 or sys.argv[1:] not in ([], ['--pin-drawing']):
        raise SystemExit('Run through t630-gnome-run as the owner [--pin-drawing].')
    from gi.repository import Gio
    pin = sys.argv[1:] == ['--pin-drawing']
    if pin and Gio.DesktopAppInfo.new('mypaint.desktop') is None:
        raise SystemExit('MyPaint is not installed; no settings changed.')
    apply(Gio.Settings, pin)
    Gio.Settings.sync()
    print('App layout updated; personal folders and favorites preserved.')


if __name__ == '__main__':
    main()
