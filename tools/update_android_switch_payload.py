#!/usr/bin/env python3
"""Update the SM-T630 Android-side Ubuntu switch payload over authorized ADB."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REMOTE = {
    ROOT / "output/dual-layout-ubuntu-v2/boot.img":
        "/data/local/tmp/t630-ubuntu-boot-v2.img",
    ROOT / "android-switcher/switch-to-ubuntu.sh":
        "/data/local/tmp/t630-switch-to-ubuntu-v2",
    ROOT / "android-switcher/update-installed-switcher.sh":
        "/data/local/tmp/t630-update-installed-switcher",
}


def run(adb: str, *arguments: str) -> str:
    return subprocess.check_output([adb, *arguments], text=True,
                                   stderr=subprocess.STDOUT)


def update(apply: bool) -> None:
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb is unavailable")
    if run(adb, "get-state").strip() != "device":
        raise RuntimeError("exactly one authorized Android device is required")
    for source, remote in REMOTE.items():
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"missing or unsafe local payload: {source}")
        subprocess.run([adb, "push", str(source), remote], check=True)
    updater = REMOTE[ROOT / "android-switcher/update-installed-switcher.sh"]
    mode = "--apply" if apply else "--check"
    result = run(adb, "shell", "su", "-c", f"sh {updater} {mode}")
    wanted = ("ANDROID_SWITCH_PAYLOAD_V2_INSTALLED_NO_PARTITION_WRITE" if apply
              else "ANDROID_SWITCH_PAYLOAD_V2_READY_NO_CHANGES")
    if wanted not in result:
        raise RuntimeError("Android-side switch payload update did not complete")
    print(result, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="atomically replace the accepted files after checking")
    args = parser.parse_args()
    update(args.apply)


if __name__ == "__main__":
    main()
