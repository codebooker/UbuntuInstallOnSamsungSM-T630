#!/usr/bin/python3
"""Resolve the owner selected during SM-T630 first-boot setup.

The configuration contains one Linux username and no shell syntax, password,
network credential, UID or path. Account metadata always comes from the local
password database so device services do not trust duplicated identity fields.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_CONFIG = Path("/etc/t630/owner")
USERNAME = re.compile(r"[a-z_][a-z0-9_-]{0,31}\Z")
LOCALE = re.compile(r"(?:C|[a-z]{2,3}(?:_[A-Z]{2})?)\.UTF-8\Z")


class AccountError(ValueError):
    """The configured owner is absent or unsafe for a desktop session."""


@dataclass(frozen=True)
class OwnerAccount:
    username: str
    uid: int
    gid: int
    home: str
    shell: str


def resolve_owner(config: Path = DEFAULT_CONFIG) -> OwnerAccount:
    try:
        raw = config.read_text(encoding="utf-8")
    except OSError as exc:
        raise AccountError(f"cannot read owner configuration: {config}") from exc

    username = raw.strip()
    if raw != username + "\n" or not USERNAME.fullmatch(username):
        raise AccountError("owner configuration must contain one valid username")

    try:
        entry = pwd.getpwnam(username)
    except KeyError as exc:
        raise AccountError(f"configured owner does not exist: {username}") from exc

    expected_home = f"/home/{username}"
    if not 1000 <= entry.pw_uid < 60000 or entry.pw_gid < 1000:
        raise AccountError("owner must be an unprivileged human account")
    if os.path.normpath(entry.pw_dir) != expected_home:
        raise AccountError(f"owner home must be {expected_home}")
    if entry.pw_shell in {"", "/bin/false", "/usr/sbin/nologin"}:
        raise AccountError("owner account must have an interactive shell")

    return OwnerAccount(
        username=entry.pw_name,
        uid=entry.pw_uid,
        gid=entry.pw_gid,
        home=entry.pw_dir,
        shell=entry.pw_shell,
    )


def resolve_locale(config: Path = Path("/etc/default/locale")) -> str:
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "C.UTF-8"
    values = [line.removeprefix("LANG=") for line in lines if line.startswith("LANG=")]
    if len(values) != 1:
        return "C.UTF-8"
    value = values[0]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value if LOCALE.fullmatch(value) else "C.UTF-8"


def shell_environment(account: OwnerAccount) -> str:
    values = {
        "T630_OWNER": account.username,
        "T630_OWNER_UID": str(account.uid),
        "T630_OWNER_GID": str(account.gid),
        "T630_OWNER_HOME": account.home,
        "T630_LOCALE": resolve_locale(),
    }
    return "\n".join(f"{key}={shlex.quote(value)}" for key, value in values.items())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "format", choices=("username", "uid", "gid", "home", "locale", "json", "env")
    )
    args = parser.parse_args()
    try:
        owner = resolve_owner(args.config)
    except AccountError as exc:
        parser.exit(1, f"t630-account: {exc}\n")

    if args.format == "locale":
        print(resolve_locale())
    elif args.format == "json":
        print(json.dumps(asdict(owner), sort_keys=True))
    elif args.format == "env":
        print(shell_environment(owner))
    else:
        print(getattr(owner, args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
