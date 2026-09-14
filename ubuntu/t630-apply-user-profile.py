#!/usr/bin/python3
"""Apply the non-secret first-boot choices inside the selected GNOME session."""

import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, "/usr/local/share/t630")
from t630_account import resolve_owner
from t630_first_boot import SetupProfile, validate_profile


def setting(schema, key, value):
    subprocess.run(
        ["/usr/bin/gsettings", "set", schema, key, value],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )


owner = resolve_owner()
if os.geteuid() != owner.uid:
    raise SystemExit("Run only inside the selected owner's GNOME session")
profile_path = Path("/etc/t630/first-boot-profile.json")
marker = Path(os.environ["XDG_CONFIG_HOME"]) / "t630-first-boot-applied"
if not profile_path.exists() or marker.exists():
    raise SystemExit(0)

profile = SetupProfile(**json.loads(profile_path.read_text(encoding="utf-8")))
validate_profile(profile)
setting("org.gnome.desktop.input-sources", "sources", f"[('xkb', '{profile.keyboard_layout}')]")
setting("org.gnome.desktop.interface", "text-scaling-factor", "1.25" if profile.large_text else "1.0")
if profile.high_contrast:
    setting("org.gnome.desktop.interface", "gtk-theme", "HighContrast")
setting("org.gnome.desktop.a11y.applications", "screen-reader-enabled", "true" if profile.screen_reader else "false")
setting("org.gnome.system.location", "enabled", "true" if profile.location_services else "false")
marker.write_text("applied\n", encoding="utf-8")
