#!/usr/bin/python3
"""Observe physical orientation and GNOME output rotation without reading input."""
import argparse
import json
import os
from pathlib import Path
import time

from gi.repository import Gio


INSTALL_ID = 'SM-T630-T630XXSBDZE3-Ubuntu-v1'


def proxy(bus, name, path, interface):
    return Gio.DBusProxy.new_for_bus_sync(
        bus, Gio.DBusProxyFlags.NONE, None, name, path, interface, None)


def output_transform(display):
    result = display.call_sync('GetCurrentState', None,
                               Gio.DBusCallFlags.NONE, 5000, None).unpack()
    logical = result[2]
    if len(logical) != 1 or logical[0][5] != [('LVDS1', 'MetaProducts Inc.',
                                               'MetaMonitor', '0xC0FFEE-1')]:
        raise RuntimeError('unexpected GNOME logical-monitor layout')
    return int(logical[0][3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=int, default=120)
    args = parser.parse_args()
    if not 10 <= args.duration <= 180:
        raise SystemExit('duration must be between 10 and 180 seconds')
    if os.getuid() != 1000:
        raise SystemExit('Run through t630-gnome-run as the tablet user')
    if Path('/etc/t630-install-id').read_text().strip() != INSTALL_ID:
        raise SystemExit('Refusing an unrecognized device installation')

    sensor = proxy(Gio.BusType.SYSTEM, 'net.hadess.SensorProxy',
                   '/net/hadess/SensorProxy', 'net.hadess.SensorProxy')
    display = proxy(Gio.BusType.SESSION, 'org.gnome.Mutter.DisplayConfig',
                    '/org/gnome/Mutter/DisplayConfig',
                    'org.gnome.Mutter.DisplayConfig')

    observations = []
    deadline = time.monotonic() + args.duration
    previous = None
    while time.monotonic() < deadline:
        orientation_value = sensor.get_cached_property('AccelerometerOrientation')
        if orientation_value is None:
            raise RuntimeError('accelerometer orientation property unavailable')
        current = (orientation_value.unpack(), output_transform(display))
        if current != previous:
            observation = {
                'seconds': round(args.duration - (deadline - time.monotonic()), 1),
                'orientation': current[0],
                'transform': current[1],
            }
            observations.append(observation)
            print(json.dumps(observation, sort_keys=True), flush=True)
            previous = current
        time.sleep(.5)

    orientations = {item['orientation'] for item in observations
                    if item['orientation'] != 'undefined'}
    transforms = {item['transform'] for item in observations}
    result = {
        'observations': observations,
        'rotation_pass': len(orientations) >= 2 and len(transforms) >= 2,
        'nonflat_orientations': sorted(orientations),
        'transforms': sorted(transforms),
    }
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['rotation_pass'] else 1)


if __name__ == '__main__':
    main()
