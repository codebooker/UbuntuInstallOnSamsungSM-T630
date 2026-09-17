#!/usr/bin/env python3
"""Stop Ubuntu, unmount linuxroot, and run the staged read-only install gate."""

from serial_link import Link


PREPARE = "/run/t630-installer/prepare-staged-install"
INSTALLER = "/run/t630-installer/install-staged-release"


def main() -> None:
    with Link() as link:
        prepared = link.run(f"sh {PREPARE}", timeout=180)
        if "INSTALLER_PREPARE_COMPLETE_LINUXROOT_UNMOUNTED_RAM_PRESERVED" not in prepared:
            raise RuntimeError("tablet did not complete orderly installer preparation")
        print(prepared, end="")
        checked = link.run(f"sh {INSTALLER} --check", timeout=300)
    print(checked, end="")
    if "INSTALLER_CHECK_PASSED_LINUXROOT_UNMOUNTED_NO_DEVICE_WRITE" not in checked:
        raise RuntimeError("tablet did not pass the final read-only installer check")


if __name__ == "__main__":
    main()
