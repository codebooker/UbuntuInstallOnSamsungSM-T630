#!/usr/bin/python3
"""Resolve the installed desktop icon theme to PNGs for Weston's launcher."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from pathlib import Path
target = Path('/usr/local/share/t630/icons')
target.mkdir(parents=True, exist_ok=True)
theme = Gtk.IconTheme.new()
theme.set_custom_theme('Humanity')
for name, icon in [('controls','preferences-system'), ('files','folder'),
                   ('editor','accessories-text-editor')]:
    path = target/(name+'.png')
    if path.exists():
        raise FileExistsError(path)
    image = theme.load_icon(icon, 24, Gtk.IconLookupFlags.FORCE_SIZE)
    image.savev(str(path), 'png', [], [])
    print(name, image.get_width(), image.get_height())
