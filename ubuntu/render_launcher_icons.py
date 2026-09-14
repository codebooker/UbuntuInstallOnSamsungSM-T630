#!/usr/bin/python3
"""Resolve the installed desktop icon theme to PNGs for Weston's launcher."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import os
from pathlib import Path
import tempfile
target = Path('/usr/local/share/t630/icons')
target.mkdir(parents=True, exist_ok=True)
theme = Gtk.IconTheme.new()
# Adwaita is pulled in by GNOME Shell and is therefore available in both the
# installer rehearsal root and the running desktop.  The explicit symbolic
# names avoid relying on Humanity's optional legacy icon aliases.
theme.set_custom_theme('Adwaita')
for name, icon in [('controls','preferences-system-symbolic'),
                   ('files','folder-symbolic'),
                   ('editor','accessories-text-editor-symbolic')]:
    path = target/(name+'.png')
    image = theme.load_icon(icon, 24, Gtk.IconLookupFlags.FORCE_SIZE)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=target)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        image.savev(str(temporary), 'png', [], [])
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(name, image.get_width(), image.get_height())
