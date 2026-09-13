#!/usr/bin/env python3
"""Minimal, isolated Android property-service compatibility socket.

This does not alter Ubuntu properties.  It only acknowledges the small set of
runtime property writes needed by preserved Android camera services.
"""

import argparse
import os
import signal
import socket
import struct
import sys


SOCKET_PATH = "/dev/socket/property_service"
PROP_MSG_SETPROP = 1
PROP_MSG_SETPROP2 = 0x00020001
PROP_SUCCESS = 0
PROP_ERROR_READ_CMD = 0x0004
PROP_ERROR_INVALID_NAME = 0x0005

# Keep this bridge deliberately narrow.  More camera properties can be added
# only after observing an actual stock component request them.
ALLOWED_NAMES = {
    "hwservicemanager.ready",
}


def recv_exact(conn: socket.socket, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = conn.recv(length - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def recv_u32(conn: socket.socket) -> int | None:
    data = recv_exact(conn, 4)
    return struct.unpack("<I", data)[0] if len(data) == 4 else None


def recv_string(conn: socket.socket) -> str | None:
    length = recv_u32(conn)
    if length is None or length > 4096:
        return None
    data = recv_exact(conn, length)
    if len(data) != length:
        return None
    return data.decode("utf-8", "replace")


def permitted(name: str) -> bool:
    return name in ALLOWED_NAMES or name.startswith("vendor.camera.")


def handle(conn: socket.socket, verbose: bool) -> None:
    command_data = recv_exact(conn, 4)
    if len(command_data) != 4:
        return
    command = struct.unpack("<I", command_data)[0]

    if command == PROP_MSG_SETPROP:
        payload = recv_exact(conn, 32 + 92)
        if len(payload) != 124:
            return
        name = payload[:32].split(b"\0", 1)[0].decode("utf-8", "replace")
        value = payload[32:].split(b"\0", 1)[0].decode("utf-8", "replace")
        if verbose:
            print(f"legacy set {name}={value}", flush=True)
        # Android's legacy client does not wait for a response.
        return

    if command == PROP_MSG_SETPROP2:
        name = recv_string(conn)
        value = recv_string(conn)
        if name is None or value is None:
            result = PROP_ERROR_READ_CMD
        elif permitted(name):
            result = PROP_SUCCESS
            if verbose:
                print(f"set {name}={value}", flush=True)
        else:
            result = PROP_ERROR_INVALID_NAME
            if verbose:
                print(f"rejected {name}={value}", flush=True)
        conn.sendall(struct.pack("<I", result))
        return

    if verbose:
        print(f"unknown command 0x{command:08x}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(SOCKET_PATH), mode=0o755, exist_ok=True)
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(8)

    def stop(_signum, _frame):
        server.close()
        try:
            os.unlink(SOCKET_PATH)
        except FileNotFoundError:
            pass
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while True:
        try:
            conn, _ = server.accept()
        except OSError:
            return 0
        with conn:
            conn.settimeout(2)
            try:
                handle(conn, args.verbose)
            except (OSError, TimeoutError):
                pass


if __name__ == "__main__":
    sys.exit(main())
