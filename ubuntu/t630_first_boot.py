#!/usr/bin/python3
"""Validated backend for the SM-T630 first-boot setup screen.

Passwords are accepted separately from the non-secret profile and are sent to
chpasswd over stdin. They are never placed in arguments, files, logs or the
profile representation. The owner marker is committed only after setup passes.
"""

from __future__ import annotations

import argparse
import grp
import json
import os
import pwd
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from t630_account import USERNAME


INSTALL_ID = "SM-T630-T630XXSBDZE3-Ubuntu-v1"
OWNER_GROUP = "t630-owner"
OPTIONAL_GROUPS = ("audio", "video", "input", "render", "plugdev", "netdev", "sudo")
HOSTNAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
LOCALE = re.compile(r"[a-z]{2,3}(?:_[A-Z]{2})?\.UTF-8\Z")
KEYBOARD = re.compile(r"[a-z][a-z0-9_-]{0,15}\Z")
TIMEZONE = re.compile(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)+\Z")


class SetupError(ValueError):
    """First-boot input or device state is unsafe."""


@dataclass(frozen=True)
class SetupProfile:
    username: str
    full_name: str
    hostname: str
    timezone: str
    locale: str = "en_US.UTF-8"
    keyboard_layout: str = "us"
    location_services: bool = False
    large_text: bool = False
    high_contrast: bool = False
    screen_reader: bool = False


def validate_profile(profile: SetupProfile, zoneinfo: Path = Path("/usr/share/zoneinfo")) -> None:
    if not USERNAME.fullmatch(profile.username):
        raise SetupError("username must use lowercase letters, numbers, hyphens or underscores")
    if profile.username in {"root", "nobody", OWNER_GROUP}:
        raise SetupError("reserved username")
    if not profile.full_name.strip() or profile.full_name != profile.full_name.strip():
        raise SetupError("full name cannot be empty or have outer whitespace")
    if len(profile.full_name) > 128 or any(c in profile.full_name for c in ":\n\r\0"):
        raise SetupError("full name contains unsupported characters")
    if not HOSTNAME.fullmatch(profile.hostname) or profile.hostname.isdigit():
        raise SetupError("invalid computer name")
    if not LOCALE.fullmatch(profile.locale):
        raise SetupError("invalid UTF-8 locale")
    if not KEYBOARD.fullmatch(profile.keyboard_layout):
        raise SetupError("invalid keyboard layout")
    if not TIMEZONE.fullmatch(profile.timezone) or ".." in profile.timezone:
        raise SetupError("invalid timezone")
    try:
        candidate = (zoneinfo / profile.timezone).resolve(strict=True)
        root = zoneinfo.resolve(strict=True)
    except OSError as exc:
        raise SetupError("timezone is not installed") from exc
    if root not in candidate.parents or not candidate.is_file():
        raise SetupError("timezone leaves the system timezone directory")


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise SetupError("password must contain at least 8 characters")
    if len(password) > 1024 or any(c in password for c in "\n\r\0"):
        raise SetupError("password contains unsupported characters")


def groups_for_owner() -> list[str]:
    existing = {entry.gr_name for entry in grp.getgrall()}
    return [OWNER_GROUP, *(name for name in OPTIONAL_GROUPS if name in existing)]


def command_plan(profile: SetupProfile, account_exists: bool) -> list[list[str]]:
    commands: list[list[str]] = []
    try:
        grp.getgrnam(OWNER_GROUP)
    except KeyError:
        commands.append(["/usr/sbin/groupadd", "--system", OWNER_GROUP])
    if not account_exists:
        commands.append([
            "/usr/sbin/useradd", "--create-home", "--user-group",
            "--shell", "/bin/bash", "--comment", profile.full_name,
            profile.username,
        ])
    commands.append([
        "/usr/sbin/usermod", "--append", "--groups",
        ",".join(groups_for_owner()), profile.username,
    ])
    return commands


def write_atomic(path: Path, value: str, mode: int = 0o644) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def account_already_valid(profile: SetupProfile) -> bool:
    try:
        entry = pwd.getpwnam(profile.username)
    except KeyError:
        return False
    if not 1000 <= entry.pw_uid < 60000:
        raise SetupError("existing username is not an unprivileged human account")
    if entry.pw_dir != f"/home/{profile.username}":
        raise SetupError("existing username has an unexpected home directory")
    return True


def run_checked(command: list[str], *, secret_input: str | None = None) -> None:
    subprocess.run(
        command,
        input=secret_input,
        text=secret_input is not None,
        stdin=subprocess.DEVNULL if secret_input is None else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )


def apply_profile(profile: SetupProfile, password: str) -> None:
    if os.geteuid() != 0:
        raise SetupError("first-boot backend must run as root")
    if Path("/etc/t630-install-id").read_text(encoding="utf-8").strip() != INSTALL_ID:
        raise SetupError("not the validated SM-T630 installation")
    owner_path = Path("/etc/t630/owner")
    if owner_path.exists():
        raise SetupError("first-boot setup is already complete")

    validate_profile(profile)
    validate_password(password)
    account_exists = account_already_valid(profile)
    for command in command_plan(profile, account_exists):
        run_checked(command)
    run_checked(["/usr/sbin/chpasswd"], secret_input=f"{profile.username}:{password}\n")
    run_checked(["/usr/sbin/locale-gen", profile.locale])

    write_atomic(Path("/etc/hostname"), profile.hostname + "\n")
    write_atomic(Path("/etc/timezone"), profile.timezone + "\n")
    write_atomic(Path("/etc/default/locale"), f"LANG={profile.locale}\n")
    write_atomic(
        Path("/etc/default/keyboard"),
        f'XKBLAYOUT="{profile.keyboard_layout}"\nXKBVARIANT=""\n',
    )
    localtime = Path("/etc/localtime")
    localtime.unlink(missing_ok=True)
    localtime.symlink_to(Path("/usr/share/zoneinfo") / profile.timezone)
    run_checked(["/bin/hostname", profile.hostname])

    write_atomic(Path("/etc/t630/first-boot-profile.json"), json.dumps(asdict(profile), sort_keys=True) + "\n")
    # Commit last: runtime services start only after every preceding step passed.
    write_atomic(owner_path, profile.username + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(args.profile.read_text(encoding="utf-8"))
        profile = SetupProfile(**payload)
        validate_profile(profile)
        if args.validate_only:
            print("FIRST_BOOT_PROFILE_VALID")
            return 0
        password = os.read(0, 4096).decode("utf-8")
        if password.endswith("\n"):
            password = password[:-1]
        apply_profile(profile, password)
    except (OSError, TypeError, json.JSONDecodeError, SetupError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"t630-first-boot: {exc}\n")
    finally:
        if "password" in locals():
            password = ""
    print("FIRST_BOOT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
