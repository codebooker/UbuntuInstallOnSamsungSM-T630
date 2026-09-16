#!/usr/bin/python3
"""Read-only GTK input inventory inside the selected normal-user session.

Does not read evdev, grab devices, inject events, or record handwriting.
Live mode enables tablet events only in this GTK client's input configuration.
Pressure-capable device enumeration is not physical pen acceptance.
"""
import gi
import argparse
import time
import statistics
import math
from gdk_pressure_value import pressure_value
from gdk_event_latency import event_age_ms

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk, GLib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--window', action='store_true', help='Bounded live proximity/pressure check')
parser.add_argument('--seconds', type=int, default=30,
                    help='Live-window duration, 15–120 seconds (default 30)')
args = parser.parse_args()
if not 15 <= args.seconds <= 120:
    parser.error('--seconds must be between 15 and 120')

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
              f'type={kind.value_nick} mode={device.get_mode().value_nick} axes={axes}')

if args.window:
    # Axes in GTK3 are cloned from the current tool at proximity-in, not at
    # idle enumeration. Do not record coordinates or render/store handwriting.
    window = Gtk.Window(title='S Pen capability check — closes automatically')
    Gtk.Settings.get_default().set_property('gtk-application-prefer-dark-theme', True)
    window.set_support_multidevice(True)
    window.set_default_size(900, 600)
    window.maximize()
    label = Gtk.Label(label='S Pen capability check\n\nHover here, then try light and firm tip pressure.\n'
                      f'No handwriting is recorded. This closes after {args.seconds} seconds.')
    surface = Gtk.EventBox()
    surface.set_support_multidevice(True)
    surface.add(label)
    window.add(surface)
    surface.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.PROXIMITY_IN_MASK |
                      Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
    for device in manager.list_devices(Gdk.DeviceType.SLAVE):
        if device.get_source() in (Gdk.InputSource.PEN, Gdk.InputSource.ERASER,
                                   Gdk.InputSource.CURSOR):
            device.set_mode(Gdk.InputMode.SCREEN)
    seen = set()
    samples = []
    event_counts = {}
    pen_ages = []
    def inspect(_window, event):
        device = event.get_source_device()
        if device is None:
            return False
        source = device.get_source().value_nick
        event_counts[source] = event_counts.get(source, 0) + 1
        axes = tuple(device.get_axis_use(i).value_nick for i in range(device.get_n_axes()))
        tool = event.get_device_tool()
        tool_type = tool.get_tool_type().value_nick if tool is not None else 'none'
        signature = (device.get_name(), source, tool_type, axes)
        if signature not in seen:
            seen.add(signature)
            print('LIVE TOOL:', signature, flush=True)
        pressure = pressure_value(event.get_axis(Gdk.AxisUse.PRESSURE))
        if pressure is not None and source in ('pen', 'eraser'):
            samples.append(pressure)
            age = event_age_ms(event.get_time(), time.monotonic() * 1000)
            if age is not None:
                pen_ages.append(age)
        label.set_text(f'S Pen capability check\n\nDevice: {device.get_name()}\n'
                       f'Source: {source}; tool: {tool_type}\n'
                       f'Axes: {", ".join(axes)}\nPressure: {pressure if pressure is not None else "not reported"}\n\n'
                       'No handwriting is recorded. This window closes automatically.')
        return False
    for signal in ('proximity-in-event', 'motion-notify-event', 'button-press-event', 'button-release-event'):
        surface.connect(signal, inspect)
    window.connect('destroy', Gtk.main_quit)
    GLib.timeout_add_seconds(args.seconds, lambda: (window.destroy(), False)[1])
    window.show_all()
    window.present()
    Gtk.main()
    print(f'LIVE SUMMARY: tools={len(seen)} samples={len(samples)} '
          f'pressure_min={min(samples) if samples else None} '
          f'pressure_max={max(samples) if samples else None} '
          f'event_counts={event_counts}', flush=True)
    if pen_ages:
        ordered = sorted(pen_ages)
        print(f'GTK_EVENT_AGE_MS: samples={len(ordered)} '
              f'median={statistics.median(ordered)} '
              f'p95={ordered[math.ceil(len(ordered) * .95) - 1]} max={max(ordered)}; '
              'delivery age only, not pen-to-pixel latency', flush=True)
    else:
        print('GTK_EVENT_AGE_MS: no validated pen timestamps; not a latency result', flush=True)
