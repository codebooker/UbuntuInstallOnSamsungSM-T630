#!/usr/bin/python3
"""Read-only GTK input inventory inside the selected normal-user session.

Does not read evdev, grab devices, inject events, or record handwriting.
Pressure-capable device enumeration is not physical pen acceptance.
"""
import gi
import argparse

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk, GLib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--window', action='store_true', help='Bounded live proximity/pressure check')
args = parser.parse_args()

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

if args.window:
    # Axes in GTK3 are cloned from the current tool at proximity-in, not at
    # idle enumeration. Do not record coordinates or render/store handwriting.
    window = Gtk.Window(title='S Pen capability check — closes automatically')
    window.set_default_size(900, 600)
    window.maximize()
    label = Gtk.Label(label='S Pen capability check\n\nHover here, then try light and firm tip pressure.\n'
                      'No handwriting is recorded. This closes after 30 seconds.')
    window.add(label)
    window.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.PROXIMITY_IN_MASK |
                      Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
    seen = set()
    samples = []
    def inspect(_window, event):
        device = event.get_source_device()
        if device is None or device.get_source() not in (Gdk.InputSource.PEN, Gdk.InputSource.ERASER):
            return False
        axes = tuple(device.get_axis_use(i).value_nick for i in range(device.get_n_axes()))
        signature = (device.get_name(), axes)
        if signature not in seen:
            seen.add(signature)
            print('LIVE TOOL:', signature, flush=True)
        success, pressure = event.get_axis(Gdk.AxisUse.PRESSURE)
        if success:
            samples.append(pressure)
        label.set_text(f'S Pen capability check\n\nDevice: {device.get_name()}\n'
                       f'Axes: {", ".join(axes)}\nPressure: {pressure if success else "not reported"}\n\n'
                       'No handwriting is recorded. This window closes automatically.')
        return False
    for signal in ('proximity-in-event', 'motion-notify-event', 'button-press-event', 'button-release-event'):
        window.connect(signal, inspect)
    window.connect('destroy', Gtk.main_quit)
    GLib.timeout_add_seconds(30, lambda: (window.destroy(), False)[1])
    window.show_all()
    window.present()
    Gtk.main()
    print(f'LIVE SUMMARY: tools={len(seen)} samples={len(samples)} '
          f'pressure_min={min(samples) if samples else None} '
          f'pressure_max={max(samples) if samples else None}', flush=True)
