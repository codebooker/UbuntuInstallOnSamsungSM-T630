#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class RemoteAccessTests(unittest.TestCase):
    def test_dispatcher_waits_for_loopback_screen_endpoint(self):
        launcher = ROOT / "ubuntu/t630-remote-start"
        subprocess.run(["sh", "-n", launcher], check=True)
        text = launcher.read_text()
        self.assertIn("^/usr/bin/python3 /usr/local/libexec/t630-screen$", text)
        self.assertIn("http://127.0.0.1:8765/", text)
        self.assertIn('test "$attempt" -lt 10', text)

    def test_clean_reboot_does_not_resolve_ubuntu_systemd_wrapper(self):
        helper = (ROOT / "ubuntu/stop-ubuntu-remote").read_text()
        launcher = (ROOT / "ubuntu/t630-remote-start").read_text()
        self.assertIn("/bin/busybox reboot -f", helper)
        self.assertIn("t630-stock-vendor", helper)
        self.assertNotIn("\nreboot -f", helper)
        self.assertIn("pre_explicit_reboot=a0ac11c", launcher)

    def test_screen_server_has_its_own_single_instance_lock(self):
        source = (ROOT / "ubuntu/t630_screen.py").read_text()
        self.assertIn("/run/t630-screen-service.lock", source)
        self.assertIn("fcntl.LOCK_EX | fcntl.LOCK_NB", source)
        self.assertIn("('127.0.0.1',8765)", source)

    def test_live_view_tracks_the_real_output_transform(self):
        source = (ROOT / "ubuntu/t630_screen.py").read_text()
        self.assertIn("/run/t630-weston-rotation.state", source)
        self.assertIn("Image.Transpose.ROTATE_180", source)
        self.assertIn("Image.Transpose.ROTATE_270", source)


if __name__ == "__main__":
    unittest.main()
