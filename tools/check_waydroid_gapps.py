#!/usr/bin/env python3
"""Read-only acceptance check for the SM-T630 Waydroid GAPPS runtime."""

import argparse
import configparser
import hashlib
import os
from pathlib import Path
import subprocess
import sys


CONFIG = Path("/var/lib/waydroid/waydroid.cfg")
IMAGE_DIR = Path("/var/lib/waydroid/images")
GAPPS_OTA = "https://ota.waydro.id/system/lineage/waydroid_arm64/GAPPS.json"
VENDOR_OTA = "https://ota.waydro.id/vendor/waydroid_arm64/MAINLINE.json"
ACCEPTED_IMAGE_SHA256 = {
    "system.img": "b21bb8508157fdd3fe0611d5770c9103403a4a0834f3713650ddcf25a6fb1578",
    "vendor.img": "b18a05747db565c134db48031caeec3ce4bd9e0ce8f88ef9c679f3ef9e24e39a",
}
REQUIRED_PACKAGES = (
    "com.android.vending",
    "com.google.android.gms",
    "com.google.android.gsf",
)


def run(command, *, timeout=20):
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def parse_status(text):
    values = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip().lower()] = value.strip()
    return values


def read_waydroid_config(path=CONFIG):
    parser = configparser.ConfigParser()
    with path.open(encoding="utf-8") as stream:
        parser.read_file(stream)
    return dict(parser["waydroid"])


def is_gapps_config(values):
    return (
        values.get("arch") == "arm64"
        and values.get("vendor_type") == "MAINLINE"
        and values.get("system_ota") == GAPPS_OTA
        and values.get("vendor_ota") == VENDOR_OTA
    )


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def android(command, *, timeout=20):
    return run(["waydroid", "shell", "--", *command], timeout=timeout)


def registration_id_available():
    # Capture the identifier only in memory and report a Boolean. Never emit it.
    script = (
        'sqlite3 /data/data/*/*/gservices.db '
        "'select value from main where name = \"android_id\";' 2>/dev/null "
        "| head -n1"
    )
    result = android(["sh", "-c", script])
    return result.returncode == 0 and bool(result.stdout.strip())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-images",
        action="store_true",
        help="also hash the multi-gigabyte images against the accepted build",
    )
    args = parser.parse_args(argv)

    if os.geteuid() != 0:
        print("Run this check as root on the tablet.", file=sys.stderr)
        return 2

    failures = []
    try:
        config = read_waydroid_config()
    except (OSError, KeyError, configparser.Error) as error:
        print(f"FAIL configuration: {error}")
        return 1

    if is_gapps_config(config):
        print("PASS official ARM64 GAPPS/MAINLINE channels configured")
    else:
        failures.append("official ARM64 GAPPS/MAINLINE channels are not configured")

    status_result = run(["waydroid", "status"])
    status = parse_status(status_result.stdout)
    container_state = status.get("container")
    if status.get("session") == "RUNNING" and container_state in ("RUNNING", "FROZEN"):
        print(f"PASS Waydroid session is running (container {container_state.lower()})")
    else:
        failures.append("Waydroid session and container are not both running")

    boot = android(["getprop", "sys.boot_completed"])
    if boot.returncode == 0 and boot.stdout.strip() == "1":
        print("PASS Android completed boot")
    else:
        failures.append("Android did not report boot completion")

    for package in REQUIRED_PACKAGES:
        result = android(["pm", "path", package])
        if result.returncode == 0 and result.stdout.startswith("package:"):
            print(f"PASS package {package}")
        else:
            failures.append(f"missing package {package}")

    gms = android(["pidof", "com.google.android.gms"])
    if gms.returncode == 0 and gms.stdout.strip():
        print("PASS Google Play services is running")
    else:
        failures.append("Google Play services is not running")

    ping = android(["ping", "-c", "1", "-W", "5", "connectivitycheck.gstatic.com"])
    if ping.returncode == 0:
        print("PASS Android DNS and outbound network")
    else:
        failures.append("Android DNS or outbound network failed")

    if registration_id_available():
        print("PASS local Google registration ID is available (value suppressed)")
    else:
        failures.append("Google registration ID is not available yet")

    if args.verify_images:
        for name, expected in ACCEPTED_IMAGE_SHA256.items():
            path = IMAGE_DIR / name
            if path.is_file() and sha256(path) == expected:
                print(f"PASS accepted {name} digest")
            else:
                failures.append(f"{name} does not match the accepted digest")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("Waydroid GAPPS acceptance passed; no account identifiers were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
