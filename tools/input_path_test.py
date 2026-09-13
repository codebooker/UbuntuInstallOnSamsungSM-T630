"""Temporary fullscreen test surface; records only events delivered to itself.

Synthetic injection is separately labelled and is not physical sensor proof.
No keyboard listener, no credentials, and an automatic 90-second close.
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import json
import time

events = []
window = Gtk.Window(title='SM-T630 input-path verification')
window.set_decorated(False)
window.fullscreen()
area = Gtk.EventBox()
area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.TOUCH_MASK)
def event(widget, e):
    device = e.get_source_device()
    item = {'time': round(time.monotonic(),3), 'type': e.type.value_nick,
            'source': device.get_source().value_nick if device else 'unknown',
            'x': round(e.x,2), 'y': round(e.y,2)}
    if hasattr(e, 'state'):
        item['button1'] = bool(e.state & Gdk.ModifierType.BUTTON1_MASK)
    if e.type in (Gdk.EventType.BUTTON_PRESS, Gdk.EventType.BUTTON_RELEASE):
        item['button'] = int(e.button)
    events.append(item)
    print(json.dumps(item), flush=True)
    return True
for name in ['button-press-event', 'button-release-event', 'motion-notify-event', 'touch-event']:
    area.connect(name, event)
label = Gtk.Label()
label.set_markup('<span size="28000">Checking the input path — no action needed</span>\n\nThis test closes automatically and does not change your settings.')
area.add(label)
window.add(area)
window.connect('destroy', Gtk.main_quit)
GLib.timeout_add_seconds(90, lambda: (window.destroy(), False)[1])
window.show_all()
Gtk.main()
