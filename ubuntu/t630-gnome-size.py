#!/usr/bin/python3
"""Set only the isolated preview's virtual monitor, never the physical output."""
import os
import time
from gi.repository import Gio, GLib
assert os.environ.get('XDG_CONFIG_HOME') == '/home/tablet/.config/t630-gnome-preview'
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
for attempt in range(20):
    try:
        state = bus.call_sync('org.gnome.Mutter.DisplayConfig',
            '/org/gnome/Mutter/DisplayConfig', 'org.gnome.Mutter.DisplayConfig',
            'GetCurrentState', None, None, Gio.DBusCallFlags.NONE, 2000, None).unpack()
        serial, monitors, logical, properties = state
        assert len(monitors) == 1 and monitors[0][0][0] == 'XWAYLAND0'
        assert properties.get('renderer') == 'xrandr'
        mode = next(m[0] for m in monitors[0][1] if m[1:3] == (1600, 1000))
        args = GLib.Variant('(uua(iiduba(ssa{sv}))a{sv})',
            (serial, 1, [(0, 0, 1.0, 0, True, [('XWAYLAND0', mode, {})])], {}))
        bus.call_sync('org.gnome.Mutter.DisplayConfig',
            '/org/gnome/Mutter/DisplayConfig', 'org.gnome.Mutter.DisplayConfig',
            'ApplyMonitorsConfig', args, None, Gio.DBusCallFlags.NONE, 3000, None)
        print('GNOME preview virtual monitor set to 1600x1000, scale 1.')
        break
    except GLib.Error:
        if attempt == 19:
            raise
        time.sleep(1)
