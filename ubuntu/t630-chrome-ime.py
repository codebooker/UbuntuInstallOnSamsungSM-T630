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
    # Keep the accessibility tree mode fixed to the smallest bundle intended
    # for on-screen interaction.  The unqualified switch can be downgraded by
    # Chrome after startup and then exposes only empty top-level AT-SPI frames.
    "--force-renderer-accessibility=on-screen",
    "--enable-features=AccessibilityOnScreenAXMode",
)
EXECUTABLE = "Exec=/usr/bin/google-chrome-stable"
CHROME_BINARY = "/opt/google/chrome/chrome"


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


def synchronize_launcher() -> bool:
    data_home = Path(os.environ["XDG_DATA_HOME"])
    target = data_home / "applications/google-chrome.desktop"
    if not SOURCE.is_file():
        if target.is_file() and target.read_text(errors="replace").startswith(MARKER):
            target.unlink()
            return True
        return False
    try:
        payload = patched_launcher(SOURCE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.read_text(encoding="utf-8") == payload:
        return False
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
        return True
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def incompatible_chrome_pids(proc: Path = Path("/proc")) -> list[int]:
    """Return this user's main Chrome processes missing required switches."""
    result: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = (entry / "status").read_text(errors="replace")
            uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
            if int(uid_line.split()[1]) != os.getuid():
                continue
            arguments = (entry / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, StopIteration, ValueError):
            continue
        decoded = [argument.decode(errors="replace") for argument in arguments if argument]
        if not decoded or decoded[0] != CHROME_BINARY or any(
            argument.startswith("--type=") for argument in decoded
        ):
            continue
        if any(flag not in decoded for flag in FLAGS):
            result.append(int(entry.name))
    return result


def terminate_incompatible_chrome() -> None:
    """Retire a pre-fix background process so the managed launcher takes effect."""
    for pid in incompatible_chrome_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


def main() -> int:
    watch = sys.argv[1:] == ["--watch"]
    if sys.argv[1:] not in ([], ["--watch"]):
        raise SystemExit("usage: t630-chrome-ime [--watch]")
    synchronize_launcher()
    terminate_incompatible_chrome()
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
        terminate_incompatible_chrome()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
