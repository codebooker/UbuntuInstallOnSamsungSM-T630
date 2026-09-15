#!/usr/bin/python3
"""Install versioned SM-T630 GNOME assets into the selected owner's session."""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, "/usr/local/share/t630")
from t630_account import resolve_owner


EXTENSION_ID = "t630-tablet-tools@local"
SOURCE = Path("/usr/local/share/t630/gnome-tablet-tools")
CONFIG_SOURCE = Path("/usr/local/share/t630/owner-config")
FILES = (
    Path("extension.js"),
    Path("metadata.json"),
    Path("schemas/org.gnome.shell.extensions.t630-tablet-tools.gschema.xml"),
)
CONFIG_FILES = (
    Path("wireplumber/bluetooth.lua.d/51-t630-bluetooth.lua"),
    Path("wireplumber/main.lua.d/51-t630-manual-alsa.lua"),
)


def source_digest(source: Path = SOURCE) -> str:
    digest = hashlib.sha256()
    for relative in FILES:
        path = source / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing or unsafe GNOME asset: {relative}")
        digest.update(str(relative).encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_enabled_extensions(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("@as "):
        value = value[4:]
    enabled = ast.literal_eval(value)
    if not isinstance(enabled, list) or not all(isinstance(item, str) for item in enabled):
        raise RuntimeError("invalid GNOME extension preference")
    return enabled


def enable_extension() -> None:
    result = subprocess.run(
        ["/usr/bin/gsettings", "get", "org.gnome.shell", "enabled-extensions"],
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    enabled = parse_enabled_extensions(result.stdout)
    if EXTENSION_ID not in enabled:
        enabled.append(EXTENSION_ID)
        subprocess.run(
            ["/usr/bin/gsettings", "set", "org.gnome.shell", "enabled-extensions", repr(enabled)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=True,
        )


def install_owner_configs(source: Path, config_home: Path) -> None:
    if not source.exists():
        return
    if not source.is_dir() or source.is_symlink():
        raise RuntimeError("unsafe owner-config source")
    for relative in CONFIG_FILES:
        source_file = source / relative
        if not source_file.is_file() or source_file.is_symlink():
            raise RuntimeError(f"missing or unsafe owner config: {relative}")
        destination = config_home / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        temporary = Path(name)
        try:
            os.fchmod(descriptor, 0o644)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(source_file.read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(destination)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)


def install(source: Path = SOURCE, data_home: Path | None = None,
            config_source: Path = CONFIG_SOURCE, config_home: Path | None = None) -> None:
    owner = resolve_owner()
    if os.geteuid() != owner.uid:
        raise RuntimeError("run only inside the selected owner's session")
    if data_home is None:
        data_home = Path(os.environ["XDG_DATA_HOME"])
    if config_home is None:
        config_home = Path(os.environ["XDG_CONFIG_HOME"])
    parent = data_home / "gnome-shell/extensions"
    target = parent / EXTENSION_ID
    marker = target / ".t630-source-sha256"
    digest = source_digest(source)
    if marker.is_file() and not marker.is_symlink() and marker.read_text().strip() == digest:
        install_owner_configs(config_source, config_home)
        enable_extension()
        return

    parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{EXTENSION_ID}.", dir=parent))
    backup = parent / f".{EXTENSION_ID}.previous"
    try:
        for relative in FILES:
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((source / relative).read_bytes())
            destination.chmod(0o644)
        subprocess.run(
            ["/usr/bin/glib-compile-schemas", str(temporary / "schemas")],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=True,
        )
        marker = temporary / ".t630-source-sha256"
        marker.write_text(digest + "\n", encoding="ascii")
        marker.chmod(0o644)
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.rename(backup)
        temporary.rename(target)
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
        if not target.exists() and backup.exists():
            backup.rename(target)
    install_owner_configs(config_source, config_home)
    enable_extension()


if __name__ == "__main__":
    install()
