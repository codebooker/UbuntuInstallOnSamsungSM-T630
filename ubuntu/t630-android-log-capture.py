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
MAX_OUTPUT_BYTES = 4 * 1024 * 1024


def encode_record(packet: bytes, timestamp: float) -> bytes:
    fields = [
        part.decode("utf-8", "replace")
        for part in re.findall(rb"[\x20-\x7e]{2,}", packet)
    ]
    if not fields:
        return b""
    return f"{timestamp:.3f} {' | '.join(fields)}\n".encode("utf-8")


def write_bounded(output, record: bytes, limit: int = MAX_OUTPUT_BYTES) -> None:
    if not record:
        return
    output.seek(0, os.SEEK_END)
    if output.tell() + len(record) > limit:
        output.seek(0)
        output.truncate()
    output.write(record)


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

    # Camera debug can be extremely verbose. Keep one bounded current log in
    # tmpfs so a long camera session cannot exhaust /run and break unrelated
    # desktop services.
    with open(OUTPUT_PATH, "a+b", buffering=0) as output:
        while True:
            try:
                packet = server.recv(65535)
            except OSError:
                return 0
            write_bounded(output, encode_record(packet, time.monotonic()))


if __name__ == "__main__":
    sys.exit(main())
