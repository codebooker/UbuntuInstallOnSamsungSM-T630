#!/usr/bin/env python3
"""Build an exact Android bootloader message for the SM-T630 recovery."""

import argparse
import hashlib
from pathlib import Path


FIELD_LAYOUT = (
    ("command", 32),
    ("status", 32),
    ("recovery", 768),
    ("stage", 32),
    ("reserved", 1184),
)
TOTAL_SIZE = sum(size for _, size in FIELD_LAYOUT)


def field(value: str, size: int) -> bytes:
    encoded = value.encode("ascii")
    if b"\0" in encoded or len(encoded) >= size:
        raise ValueError("bootloader-message field does not fit")
    return encoded + bytes(size - len(encoded))


def build_message(recovery_arguments: tuple[str, ...], *, allow_wipe: bool) -> bytes:
    values = {
        "command": "boot-recovery",
        "status": "",
        "recovery": "recovery\n" + "".join(f"{argument}\n" for argument in recovery_arguments),
        "stage": "",
        "reserved": "",
    }
    message = b"".join(field(values[name], size) for name, size in FIELD_LAYOUT)
    if len(message) != TOTAL_SIZE:
        raise AssertionError("bootloader-message size changed")
    if not allow_wipe and b"wipe" in message.lower():
        raise AssertionError("preflight BCB unexpectedly contains a wipe request")
    return message


def build_preflight_message() -> bytes:
    return build_message(
        (
            "--reason=t630_dualboot_recovery_preflight",
            "--locale=en-US",
        ),
        allow_wipe=False,
    )


def build_wipe_data_message() -> bytes:
    message = build_message(
        (
            "--wipe_data",
            "--reason=t630_dualboot_native_android_initialization",
            "--locale=en-US",
        ),
        allow_wipe=True,
    )
    recovery = message[64:832].split(b"\0", 1)[0]
    if recovery.count(b"--wipe_data\n") != 1:
        raise AssertionError("wipe BCB must contain exactly one wipe_data request")
    return message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("preflight", "wipe-data"), default="preflight"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    builders = {
        "preflight": build_preflight_message,
        "wipe-data": build_wipe_data_message,
    }
    message = builders[args.mode]()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(message)
    print(f"size={len(message)}")
    print(f"sha256={hashlib.sha256(message).hexdigest()}")
    print(f"mode={args.mode}")


if __name__ == "__main__":
    main()
