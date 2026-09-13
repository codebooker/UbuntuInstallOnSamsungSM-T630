#!/usr/bin/env python3
"""Capture printable records sent to Android's logdw socket."""

import os
import re
import signal
import socket
import sys
import time


SOCKET_PATH = "/dev/socket/logdw"
OUTPUT_PATH = "/run/t630-android-log.txt"


def main() -> int:
    os.makedirs(os.path.dirname(SOCKET_PATH), mode=0o755, exist_ok=True)
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o666)

    def stop(_signum, _frame):
        server.close()
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    with open(OUTPUT_PATH, "a", buffering=1) as output:
        while True:
            try:
                packet = server.recv(65535)
            except OSError:
                return 0
            fields = [
                part.decode("utf-8", "replace")
                for part in re.findall(rb"[\x20-\x7e]{2,}", packet)
            ]
            if fields:
                output.write(f"{time.monotonic():.3f} {' | '.join(fields)}\n")


if __name__ == "__main__":
    sys.exit(main())
