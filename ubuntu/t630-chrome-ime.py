#!/usr/bin/python3
"""Keep Google Chrome's Wayland text-input support enabled for GNOME's OSK."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import sys
import tempfile
import time


SOURCE = Path("/usr/share/applications/google-chrome.desktop")
MARKER = "# Managed by t630-chrome-ime; regenerated from the system launcher.\n"
FLAGS = (
    "--enable-wayland-ime",
    "--wayland-text-input-version=3",
    # Chrome otherwise publishes only empty top-level AT-SPI frames until a
    # screen reader connects. The owner-session OSK watcher needs editable
    # focus, not page contents, and this switch makes that state available.
    "--force-renderer-accessibility",
)
EXECUTABLE = "Exec=/usr/bin/google-chrome-stable"


def patched_launcher(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith(EXECUTABLE):
            command, newline = line.rstrip("\n"), "\n" if line.endswith("\n") else ""
            missing = [flag for flag in FLAGS if flag not in command]
            if missing:
                executable, separator, arguments = command.partition(" ")
                command = executable + " " + " ".join(missing)
                if separator:
                    command += " " + arguments
            line = command + newline
        lines.append(line)
    return MARKER + "".join(lines)


def synchronize_launcher() -> None:
    data_home = Path(os.environ["XDG_DATA_HOME"])
    target = data_home / "applications/google-chrome.desktop"
    if not SOURCE.is_file():
        if target.is_file() and target.read_text(errors="replace").startswith(MARKER):
            target.unlink()
        return
    try:
        payload = patched_launcher(SOURCE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.read_text(encoding="utf-8") == payload:
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=".google-chrome.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def main() -> int:
    watch = sys.argv[1:] == ["--watch"]
    if sys.argv[1:] not in ([], ["--watch"]):
        raise SystemExit("usage: t630-chrome-ime [--watch]")
    synchronize_launcher()
    if not watch:
        return 0
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        time.sleep(2)
        synchronize_launcher()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
