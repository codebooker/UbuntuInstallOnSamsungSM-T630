#!/usr/bin/python3
"""Temporary typing test; observes only its own non-secret test field."""
import json
from pathlib import Path
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib
window = Gtk.Window(title='Automatic keyboard check — temporary window')
window.set_default_size(1000,500)
window.set_border_width(24)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
window.add(box)
title = Gtk.Label(label='Automatic keyboard check — no typing needed', xalign=0)
box.pack_start(title,False,False,0)
box.pack_start(Gtk.Label(label='Checking typing, backspace and Enter. Your documents stay open.',xalign=0),False,False,0)
view = Gtk.TextView()
view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
box.pack_start(view,True,True,0)
status = Gtk.Label(label='Type: tablet',xalign=0)
box.pack_start(status,False,False,0)
def changed(buffer):
    text = buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)
    passed = text.strip() == 'tablet'
    status.set_text('Typing test passed.' if passed else 'Type: tablet')
    Path('/run/user/1000/t630-keyboard-validation.json').write_text(json.dumps({'expected_text_received':passed,'character_count':len(text),'newline_received':'\n' in text,'test_driver':'synthetic_OSK_clicks_planned'}))
view.get_buffer().connect('changed',changed)
window.connect('destroy',Gtk.main_quit)
window.show_all()
view.grab_focus()
GLib.timeout_add_seconds(90, lambda: (window.destroy(),False)[1])
Gtk.main()
