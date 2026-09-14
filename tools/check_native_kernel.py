#!/usr/bin/env python3
"""Reject native SM-T630 kernel configurations that break the tested ABI."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


REQUIRED = {
    "CONFIG_LOCALVERSION": '"-qgki-31225846-abT630XXSBDZE3"',
    "CONFIG_MODULES": "y",
    "CONFIG_MODVERSIONS": "y",
    "CONFIG_BT": "y",
    "CONFIG_BT_HCIUART": "y",
    "CONFIG_BT_HCIUART_H4": "y",
    "CONFIG_BT_HCIUART_QCA": "y",
    "CONFIG_SAMSUNG_NFC": "m",
}

DEFERRED = {
    "CONFIG_SYSVIPC",
    "CONFIG_CGROUP_PIDS",
    "CONFIG_CGROUP_DEVICE",
    "CONFIG_USER_NS",
    "CONFIG_PID_NS",
    "CONFIG_IPC_NS",
    "CONFIG_NETFILTER_XT_TARGET_CHECKSUM",
}


def parse_config(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
            continue
        match = re.fullmatch(r"# (CONFIG_[A-Z0-9_]+) is not set", line)
        if match:
            values[match.group(1)] = "n"
    return values


def validate(path: Path) -> None:
    values = parse_config(path)
    problems = []
    for key, expected in REQUIRED.items():
        actual = values.get(key, "missing")
        if actual != expected:
            problems.append(f"{key}: expected {expected}, found {actual}")
    for key in sorted(DEFERRED):
        actual = values.get(key, "n")
        if actual not in {"n", "missing"}:
            problems.append(f"{key}: {actual} would change the audited module ABI")
    if problems:
        raise SystemExit("Native kernel configuration rejected:\n- " + "\n- ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    validate(args.config)
    print("Native SM-T630 kernel configuration preserves the tested feature boundary.")


if __name__ == "__main__":
    main()
