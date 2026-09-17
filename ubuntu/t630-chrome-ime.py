#!/usr/bin/python3
"""Keep Google Chrome's Wayland text-input support enabled for GNOME's OSK."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


SOURCE = Path("/usr/share/applications/google-chrome.desktop")
MARKER = "# Managed by t630-chrome-ime; regenerated from the system launcher.\n"
FLAGS = ("--enable-wayland-ime", "--wayland-text-input-version=3")
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


def main() -> int:
    data_home = Path(os.environ["XDG_DATA_HOME"])
    target = data_home / "applications/google-chrome.desktop"
    if not SOURCE.is_file():
        if target.is_file() and target.read_text(errors="replace").startswith(MARKER):
            target.unlink()
        return 0
    payload = patched_launcher(SOURCE.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
