#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    "camera/t630-camera-mounts.sh",
    "ubuntu/49-t630-sensorproxy.rules",
    "ubuntu/configure-everyday-desktop.sh",
    "ubuntu/t630-app",
    "ubuntu/t630-audio-session-cleanup.py",
    "ubuntu/t630-audio-start",
    "ubuntu/t630-auth-watch.py",
    "ubuntu/t630-camera-app",
    "ubuntu/t630-camera-bridge",
    "ubuntu/t630-camera-sudoers",
    "ubuntu/t630-desktop-autostart",
    "ubuntu/t630-gnome-preview",
    "ubuntu/t630-gnome-run.py",
    "ubuntu/t630-gnome-size.py",
    "ubuntu/t630-gpu-session-watch.py",
    "ubuntu/t630-install-owner-assets.py",
    "ubuntu/t630-lock-on-start.py",
    "ubuntu/t630-managed-session.py",
    "ubuntu/t630-microphone-bridge",
    "ubuntu/t630-power-button.py",
    "ubuntu/t630-rotation-controller.py",
    "ubuntu/t630-session-manager.py",
    "ubuntu/t630-user-app",
    "ubuntu/t630-x11-recovery.py",
    "ubuntu/t630_controls.py",
    "ubuntu/t630_display.py",
)
FORBIDDEN = (
    "/home/tablet",
    "/run/user/1000",
    "USER=tablet",
    "LOGNAME=tablet",
    "id -u tablet",
    "pgrep -u 1000",
    "subject.user == \"tablet\"",
    "tablet ALL=(root)",
    "os.getuid() == 1000",
    "os.getuid() != 1000",
    "os.geteuid() == 1000",
    "os.geteuid() != 1000",
)


class OwnerIndependenceTests(unittest.TestCase):
    def test_runtime_integration_has_no_development_identity(self):
        for relative in RUNTIME_FILES:
            text = (ROOT / relative).read_text()
            for forbidden in FORBIDDEN:
                with self.subTest(file=relative, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)

    def test_privileged_desktop_access_uses_installer_owner_group(self):
        sensor = (ROOT / "ubuntu/49-t630-sensorproxy.rules").read_text()
        camera = (ROOT / "ubuntu/t630-camera-sudoers").read_text()
        rotation = (ROOT / "ubuntu/t630-weston-rotation.c").read_text()
        self.assertIn('subject.isInGroup("t630-owner")', sensor)
        self.assertIn("\n%t630-owner ", camera)
        self.assertIn('getgrnam("t630-owner")', rotation)


if __name__ == "__main__":
    unittest.main()
