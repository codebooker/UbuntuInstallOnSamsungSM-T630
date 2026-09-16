#!/usr/bin/env python3
"""Explicitly authorize and run the already-staged destructive SM-T630 install."""

from __future__ import annotations

import argparse

from serial_link import Link


PHRASE = "ERASE SM-T630 USERDATA"
TOKEN = "ERASE SM-T630 USERDATA /dev/sda34 226918360"
INSTALLER = "/run/t630-installer/install-staged-release"
AUTHORIZATION = "/run/t630-installer/ERASE-SM-T630-USERDATA"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--acknowledge-stock-recovery",
        action="store_true",
        help="confirm the matching factory archive was retained and verified")
    args = parser.parse_args()
    if not args.acknowledge_stock_recovery:
        parser.error("--acknowledge-stock-recovery is required")

    print("This permanently erases Android userdata on the connected SM-T630.")
    print("The operation cannot preserve files from Android or the current Ubuntu root.")
    print(f"Type exactly: {PHRASE}")
    if input("> ") != PHRASE:
        raise SystemExit("Confirmation did not match; nothing was changed.")

    with Link() as link:
        checked = link.run(f"sh {INSTALLER} --check", timeout=240)
        if "INSTALLER_CHECK_PASSED_USERDATA_UNMOUNTED_NO_DEVICE_WRITE" not in checked:
            raise RuntimeError("final tablet-side check failed; authorization was not created")
        authorize = link.run(
            "set -eu; umask 077; set -C; "
            f"printf '%s\\n' '{TOKEN}' >'{AUTHORIZATION}'; "
            f"test \"$(cat '{AUTHORIZATION}')\" = '{TOKEN}'; "
            "echo INSTALLER_ERASE_TOKEN_CREATED_ONCE",
            timeout=30)
        if "INSTALLER_ERASE_TOKEN_CREATED_ONCE" not in authorize:
            raise RuntimeError("tablet did not accept the one-time authorization token")
        result = link.run(f"sh {INSTALLER} --apply", timeout=1800)
    print(result, end="")
    if "INSTALLER_APPLY_COMPLETE_ROOT_VERIFIED_REBOOT_REQUIRED" not in result:
        raise RuntimeError(
            "installation did not reach verified completion; do not reboot blindly")
    print("Installation verified. Reboot from the recovery console when ready.")


if __name__ == "__main__":
    main()
