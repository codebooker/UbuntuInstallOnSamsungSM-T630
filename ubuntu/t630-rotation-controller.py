#!/usr/bin/python3
"""Apply stable, absolute display rotations for the SM-T630 GNOME session.

The tablet's accelerometer is mounted 90 degrees from the real panel axes.
Mutter's nested dummy monitor changes its logical size but does not rotate the
real scanout. The session therefore keeps Mutter at transform 0 and sends an
absolute, debounced transform to the Weston module that owns the DRM output.
"""

import os
from pathlib import Path
import subprocess
import time


INSTALL_ID = "SM-T630-T630XXSBDZE3-Ubuntu-v1"
MONITOR_ID = ("LVDS1", "MetaProducts Inc.", "MetaMonitor", "0xC0FFEE-1")
SETTLE_SECONDS = 1.0
ROTATION_FIFO = Path("/run/t630-weston-rotation")
ROTATION_STATE = Path("/run/t630-weston-rotation.state")

# The raw panel needs rotate-90 (Wayland transform 1) in ordinary landscape.
# Continue clockwise from that calibrated physical position.
ORIENTATION_TRANSFORMS = {
    "normal": 0,
    "bottom-up": 2,
    "left-up": 1,
    "right-up": 3,
}
TRANSFORM_MODES = {
    0: (1200, 1920),
    1: (1920, 1200),
    2: (1200, 1920),
    3: (1920, 1200),
}
PORTRAIT_MODE = "1200x1920_60.00"
PORTRAIT_MODELINE = [
    PORTRAIT_MODE, "196.50", "1200", "1296", "1424", "1648",
    "1920", "1923", "1933", "1989", "-hsync", "+vsync",
]


def mapped_transform(orientation):
    """Return the absolute Mutter transform, or None for an unusable reading."""
    return ORIENTATION_TRANSFORMS.get(orientation)


def main():
    from gi.repository import Gio, GLib

    if os.getuid() != 1000:
        raise SystemExit("Run through t630-gnome-run as the tablet user")
    if Path("/etc/t630-install-id").read_text().strip() != INSTALL_ID:
        raise SystemExit("Refusing an unrecognized device installation")

    sensor = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SYSTEM,
        Gio.DBusProxyFlags.NONE,
        None,
        "net.hadess.SensorProxy",
        "/net/hadess/SensorProxy",
        "net.hadess.SensorProxy",
        None,
    )
    display = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.gnome.Mutter.DisplayConfig",
        "/org/gnome/Mutter/DisplayConfig",
        "org.gnome.Mutter.DisplayConfig",
        None,
    )

    state = {
        "pending": None,
        "since": 0.0,
        "last_applied": None,
        "last_verify": 0.0,
        "claimed": False,
    }

    def read_orientation():
        value = sensor.get_cached_property("AccelerometerOrientation")
        return value.unpack() if value is not None else "undefined"

    def queue_orientation(orientation):
        target = mapped_transform(orientation)
        if target is None:
            return
        if state["pending"] != orientation:
            state["pending"] = orientation
            state["since"] = time.monotonic()

    def ensure_xwayland_mode(width, height):
        mode = "1920x1200" if (width, height) == (1920, 1200) else PORTRAIT_MODE
        if mode == PORTRAIT_MODE:
            subprocess.run(
                ["xrandr", "--newmode", *PORTRAIT_MODELINE],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                ["xrandr", "--addmode", "XWAYLAND0", mode],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        subprocess.run(
            ["xrandr", "--output", "XWAYLAND0", "--mode", mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

    def ensure_gnome_mode(width, height):
        result = display.call_sync(
            "GetCurrentState", None, Gio.DBusCallFlags.NONE, 5000, None
        ).unpack()
        serial, monitors, logical, _properties = result
        if len(monitors) != 1 or tuple(monitors[0][0]) != MONITOR_ID:
            raise RuntimeError("unexpected GNOME monitor identity")
        if len(logical) != 1 or [tuple(item) for item in logical[0][5]] != [MONITOR_ID]:
            raise RuntimeError("unexpected GNOME logical-monitor layout")
        mode = next(
            (item[0] for item in monitors[0][1]
             if (int(item[1]), int(item[2])) == (width, height)), None
        )
        if mode is None:
            raise RuntimeError(f"GNOME mode {width}x{height} is unavailable")
        current_mode = next(
            (item[0] for item in monitors[0][1] if item[6].get("is-current", False)),
            None,
        )
        if current_mode == mode and int(logical[0][3]) == 0:
            return False
        config = GLib.Variant(
            "(uua(iiduba(ssa{sv}))a{sv})",
            (
                serial,
                1,  # temporary: recalculate from the sensor after every login
                [(0, 0, float(logical[0][2]), 0, True, [(MONITOR_ID[0], mode, {})])],
                {},
            ),
        )
        display.call_sync(
            "ApplyMonitorsConfig", config, Gio.DBusCallFlags.NONE, 5000, None
        )
        return True

    def apply_transform(target):
        width, height = TRANSFORM_MODES[target]
        if target != state["last_applied"]:
            ensure_xwayland_mode(width, height)
        gnome_changed = ensure_gnome_mode(width, height)
        try:
            current = int(ROTATION_STATE.read_text().strip())
        except (OSError, ValueError):
            current = None
        if current == target:
            return gnome_changed
        descriptor = os.open(ROTATION_FIFO, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(descriptor, f"{target}\n".encode("ascii"))
        finally:
            os.close(descriptor)
        return True

    def properties_changed(_proxy, _changed, _invalidated):
        queue_orientation(read_orientation())

    def poll():
        try:
            if not state["claimed"]:
                sensor.call_sync(
                    "ClaimAccelerometer", None, Gio.DBusCallFlags.NONE, 5000, None
                )
                state["claimed"] = True
                queue_orientation(read_orientation())

            orientation = read_orientation()
            queue_orientation(orientation)
            if (
                state["pending"] is not None
                and time.monotonic() - state["since"] >= SETTLE_SECONDS
            ):
                target = mapped_transform(state["pending"])
                now = time.monotonic()
                if (target != state["last_applied"]
                        or now - state["last_verify"] >= 1.0):
                    previous_target = state["last_applied"]
                    changed = apply_transform(target)
                    if changed or target != previous_target:
                        print(
                            f"orientation={state['pending']} transform={target} "
                            f"mode={TRANSFORM_MODES[target][0]}x{TRANSFORM_MODES[target][1]} "
                            f"changed={changed}",
                            flush=True,
                        )
                    state["last_applied"] = target
                    state["last_verify"] = now
        except (GLib.Error, OSError, RuntimeError,
                subprocess.CalledProcessError) as error:
            print(f"rotation retry: {error}", flush=True)
            state["last_applied"] = None
        return GLib.SOURCE_CONTINUE

    sensor.connect("g-properties-changed", properties_changed)
    GLib.timeout_add(250, poll)
    poll()
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()
