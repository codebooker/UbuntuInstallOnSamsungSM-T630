#!/usr/bin/python3
"""Observe physical orientation and GNOME output rotation without reading input."""
import argparse
import json
import os
from pathlib import Path
import time

from gi.repository import Gio


INSTALL_ID = 'SM-T630-T630XXSBDZE3-Ubuntu-v1'
EXPECTED_TRANSFORMS = {
    'normal': 0,
    'bottom-up': 2,
    'left-up': 1,
    'right-up': 3,
}
EXPECTED_MODES = {
    0: (1200, 1920),
    1: (1920, 1200),
    2: (1200, 1920),
    3: (1920, 1200),
}
ROTATION_STATE = Path('/run/t630-weston-rotation.state')
SETTLE_SECONDS = 1.5


def proxy(bus, name, path, interface):
    return Gio.DBusProxy.new_for_bus_sync(
        bus, Gio.DBusProxyFlags.NONE, None, name, path, interface, None)


def output_state(display):
    result = display.call_sync('GetCurrentState', None,
                               Gio.DBusCallFlags.NONE, 5000, None).unpack()
    monitors, logical = result[1], result[2]
    identity = ('LVDS1', 'MetaProducts Inc.', 'MetaMonitor', '0xC0FFEE-1')
    if len(monitors) != 1 or tuple(monitors[0][0]) != identity:
        raise RuntimeError('unexpected GNOME monitor identity')
    if len(logical) != 1 or logical[0][5] != [('LVDS1', 'MetaProducts Inc.',
                                               'MetaMonitor', '0xC0FFEE-1')]:
        raise RuntimeError('unexpected GNOME logical-monitor layout')
    current = next((mode for mode in monitors[0][1]
                    if mode[6].get('is-current', False)), None)
    if current is None:
        raise RuntimeError('GNOME current mode unavailable')
    return (int(current[1]), int(current[2])), int(logical[0][3])


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
    previous_orientation = None
    orientation_since = 0.0
    previous_stable = None
    while time.monotonic() < deadline:
        orientation_value = sensor.get_cached_property('AccelerometerOrientation')
        if orientation_value is None:
            raise RuntimeError('accelerometer orientation property unavailable')
        orientation = orientation_value.unpack()
        now = time.monotonic()
        if orientation != previous_orientation:
            previous_orientation = orientation
            orientation_since = now
        if orientation not in EXPECTED_TRANSFORMS or now - orientation_since < SETTLE_SECONDS:
            time.sleep(.25)
            continue
        expected_transform = EXPECTED_TRANSFORMS[orientation]
        mode, gnome_transform = output_state(display)
        weston_transform = int(ROTATION_STATE.read_text().strip())
        current = (orientation, weston_transform, mode, gnome_transform)
        if current != previous_stable:
            observation = {
                'seconds': round(args.duration - (deadline - time.monotonic()), 1),
                'orientation': current[0],
                'weston_transform': current[1],
                'mode': list(current[2]),
                'gnome_transform': current[3],
                'expected_weston_transform': expected_transform,
                'expected_mode': list(EXPECTED_MODES[expected_transform]),
            }
            observations.append(observation)
            print(json.dumps(observation, sort_keys=True), flush=True)
            previous_stable = current
        time.sleep(.25)

    orientations = {item['orientation'] for item in observations
                    if item['orientation'] != 'undefined'}
    transforms = {item['weston_transform'] for item in observations}
    mismatches = [item for item in observations
                  if (item['weston_transform'] != item['expected_weston_transform']
                      or tuple(item['mode']) != tuple(item['expected_mode'])
                      or item['gnome_transform'] != 0)]
    result = {
        'observations': observations,
        'rotation_pass': (len(orientations) >= 2 and len(transforms) >= 2
                          and not mismatches),
        'nonflat_orientations': sorted(orientations),
        'transforms': sorted(transforms),
        'mismatches': mismatches,
    }
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['rotation_pass'] else 1)


if __name__ == '__main__':
    main()
