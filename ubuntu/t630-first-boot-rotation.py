#!/usr/bin/python3
"""Drive the physical Weston transform during ownerless first boot."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import time

from gi.repository import Gio, GLib


ROTATION_FIFO = Path("/run/t630-weston-rotation")
ORIENTATION_TRANSFORMS = {
    "normal": 0,
    "bottom-up": 2,
    "left-up": 1,
    "right-up": 3,
}
SETTLE_SECONDS = 1.0


def main() -> None:
    if os.geteuid() != 0:
        raise SystemExit("first-boot rotation requires root")
    sensor = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SYSTEM,
        Gio.DBusProxyFlags.NONE,
        None,
        "net.hadess.SensorProxy",
        "/net/hadess/SensorProxy",
        "net.hadess.SensorProxy",
        None,
    )
    sensor.call_sync("ClaimAccelerometer", None, Gio.DBusCallFlags.NONE, 5000, None)
    pending = None
    pending_since = 0.0
    applied = None
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        while not stopping:
            value = sensor.get_cached_property("AccelerometerOrientation")
            orientation = value.unpack() if value is not None else "undefined"
            target = ORIENTATION_TRANSFORMS.get(orientation)
            now = time.monotonic()
            if target is not None and target != pending:
                pending = target
                pending_since = now
            if pending is not None and pending != applied and now - pending_since >= SETTLE_SECONDS:
                descriptor = os.open(ROTATION_FIFO, os.O_WRONLY | os.O_NONBLOCK)
                try:
                    os.write(descriptor, f"{pending}\n".encode("ascii"))
                finally:
                    os.close(descriptor)
                applied = pending
                print(f"first-boot physical transform={applied}", flush=True)
            time.sleep(0.25)
    finally:
        try:
            sensor.call_sync(
                "ReleaseAccelerometer", None, Gio.DBusCallFlags.NONE, 5000, None
            )
        except GLib.Error:
            pass


if __name__ == "__main__":
    main()
