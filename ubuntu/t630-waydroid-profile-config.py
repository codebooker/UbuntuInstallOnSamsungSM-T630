#!/usr/bin/python3
"""Atomically persist or restore the SM-T630 Waydroid render dimensions."""

from __future__ import annotations

import configparser
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


CONFIG = Path("/var/lib/waydroid/waydroid.cfg")
STATE = Path("/var/lib/waydroid/t630-software-profile.config-before.json")
LOCK = Path("/var/lib/waydroid/t630-software-profile.lock")
INSTALL_ID = Path("/etc/t630-install-id")
DEVICE_ID = "SM-T630-T630XXSBDZE3-Ubuntu-v1"
SECTION = "properties"
VALUES = {
    "persist.waydroid.width": "1024",
    "persist.waydroid.height": "623",
}


def safe_regular(path: Path, required_uid: int = 0) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != required_uid:
        raise RuntimeError(f"unsafe root-owned file: {path}")
    return info


def load_config(path: Path, required_uid: int = 0) -> tuple[configparser.ConfigParser, os.stat_result]:
    info = safe_regular(path, required_uid)
    parser = configparser.ConfigParser(interpolation=None)
    with path.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    if not parser.has_section("waydroid") or not parser.has_section(SECTION):
        raise RuntimeError("unexpected Waydroid configuration")
    return parser, info


def atomic_config_write(path: Path, parser: configparser.ConfigParser,
                        info: os.stat_result) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, stat.S_IMODE(info.st_mode))
        os.fchown(descriptor, info.st_uid, info.st_gid)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            parser.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def atomic_state_write(path: Path, value: dict[str, str | None]) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            json.dump({"version": 1, "properties": value}, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def validate_saved(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict) or value.get("version") != 1:
        raise RuntimeError("invalid saved Waydroid configuration version")
    properties = value.get("properties")
    if not isinstance(properties, dict) or set(properties) != set(VALUES):
        raise RuntimeError("invalid saved Waydroid property set")
    for item in properties.values():
        if item is not None and (not isinstance(item, str) or not item.isdigit()):
            raise RuntimeError("invalid saved Waydroid property value")
    return properties


def update(action: str, config: Path = CONFIG, state: Path = STATE,
           lock: Path = LOCK, required_uid: int = 0) -> None:
    if os.geteuid() != required_uid:
        raise RuntimeError("Waydroid profile configuration requires root")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="ascii") as lock_stream:
        os.fchmod(lock_stream.fileno(), 0o600)
        fcntl.flock(lock_stream, fcntl.LOCK_EX)
        parser, info = load_config(config, required_uid)
        if action == "apply":
            if state.exists():
                safe_regular(state, required_uid)
                validate_saved(json.loads(state.read_text(encoding="utf-8")))
            else:
                previous = {
                    key: parser.get(SECTION, key) if parser.has_option(SECTION, key) else None
                    for key in VALUES
                }
                validate_saved({"version": 1, "properties": previous})
                atomic_state_write(state, previous)
            for key, value in VALUES.items():
                parser.set(SECTION, key, value)
            atomic_config_write(config, parser, info)
        elif action == "restore":
            safe_regular(state, required_uid)
            previous = validate_saved(json.loads(state.read_text(encoding="utf-8")))
            for key, value in previous.items():
                if value is None:
                    parser.remove_option(SECTION, key)
                else:
                    parser.set(SECTION, key, value)
            atomic_config_write(config, parser, info)
            state.unlink()
        elif action == "status":
            for key in VALUES:
                print(f"config.{key}={parser.get(SECTION, key, fallback='')}")
        else:
            raise RuntimeError("expected apply, restore, or status")


def main() -> None:
    if INSTALL_ID.read_text(encoding="ascii").strip() != DEVICE_ID:
        raise SystemExit("unexpected device installation")
    if len(sys.argv) != 2:
        raise SystemExit("Usage: t630-waydroid-profile-config {apply|restore|status}")
    update(sys.argv[1])


if __name__ == "__main__":
    main()
