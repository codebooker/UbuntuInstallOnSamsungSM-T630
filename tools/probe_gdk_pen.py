#!/usr/bin/python3
"""Read-only GTK input inventory inside the selected normal-user session.

Does not read evdev, grab devices, inject events, or record handwriting.
Pressure-capable device enumeration is not physical pen acceptance.
"""
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

Gtk.init([])
display = Gdk.Display.get_default()
if display is None:
    raise SystemExit('No GTK display available.')
manager = display.get_device_manager()
print('Display:', display.get_name())
for kind in (Gdk.DeviceType.MASTER, Gdk.DeviceType.SLAVE, Gdk.DeviceType.FLOATING):
    for device in manager.list_devices(kind):
        axes = [] if device.get_source() == Gdk.InputSource.KEYBOARD else [
            device.get_axis_use(i).value_nick for i in range(device.get_n_axes())]
        print(f'{device.get_name()}: source={device.get_source().value_nick} '
              f'type={kind.value_nick} axes={axes}')
