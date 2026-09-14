#!/usr/bin/python3
"""Keep the disposable GNOME installer matched to the physical panel shape."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

from gi.repository import Gio, GLib


MONITOR_ID = ("LVDS1", "MetaProducts Inc.", "MetaMonitor", "0xC0FFEE-1")
ROTATION_STATE = Path("/run/t630-weston-rotation.state")
TRANSFORM_MODES = {0: (1200, 1920), 1: (1920, 1200),
                   2: (1200, 1920), 3: (1920, 1200)}
PORTRAIT_MODE = "1200x1920_60.00"
PORTRAIT_MODELINE = [
    PORTRAIT_MODE, "196.50", "1200", "1296", "1424", "1648",
    "1920", "1923", "1933", "1989", "-hsync", "+vsync",
]


def ensure_xwayland_mode(width: int, height: int) -> None:
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


def ensure_gnome_mode(display, width: int, height: int) -> None:
    serial, monitors, logical, _properties = display.call_sync(
        "GetCurrentState", None, Gio.DBusCallFlags.NONE, 5000, None
    ).unpack()
    if len(monitors) != 1 or tuple(monitors[0][0]) != MONITOR_ID:
        raise RuntimeError("unexpected installer monitor identity")
    if len(logical) != 1 or [tuple(item) for item in logical[0][5]] != [MONITOR_ID]:
        raise RuntimeError("unexpected installer logical-monitor layout")
    mode = next(
        (item[0] for item in monitors[0][1]
         if (int(item[1]), int(item[2])) == (width, height)),
        None,
    )
    if mode is None:
        raise RuntimeError(f"installer mode {width}x{height} is unavailable")
    current = next(
        (item[0] for item in monitors[0][1] if item[6].get("is-current", False)),
        None,
    )
    if current == mode and int(logical[0][3]) == 0:
        return
    config = GLib.Variant(
        "(uua(iiduba(ssa{sv}))a{sv})",
        (serial, 1, [(0, 0, float(logical[0][2]), 0, True,
                      [(MONITOR_ID[0], mode, {})])], {}),
    )
    display.call_sync(
        "ApplyMonitorsConfig", config, Gio.DBusCallFlags.NONE, 5000, None
    )


def main() -> None:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", ""))
    if os.geteuid() == 0 or runtime != Path("/run/t630-first-boot-session/runtime"):
        raise SystemExit("Run only inside the disposable first-boot session")
    display = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.gnome.Mutter.DisplayConfig",
        "/org/gnome/Mutter/DisplayConfig",
        "org.gnome.Mutter.DisplayConfig",
        None,
    )
    applied = None
    while True:
        try:
            target = int(ROTATION_STATE.read_text().strip())
            if target not in TRANSFORM_MODES:
                raise ValueError("invalid physical transform")
            if target != applied:
                width, height = TRANSFORM_MODES[target]
                ensure_xwayland_mode(width, height)
                ensure_gnome_mode(display, width, height)
                applied = target
                print(f"installer transform={target} mode={width}x{height}", flush=True)
        except (GLib.Error, OSError, RuntimeError, ValueError,
                subprocess.CalledProcessError) as error:
            applied = None
            print(f"installer resize retry: {error}", flush=True)
        time.sleep(0.25)


if __name__ == "__main__":
    main()
