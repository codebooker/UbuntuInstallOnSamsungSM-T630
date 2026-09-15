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
        self.assertIn('/bin/busybox "$action" -f', helper)
        self.assertIn('reboot|poweroff', helper)
        self.assertIn("t630-stock-vendor", helper)
        self.assertNotIn("\nreboot -f", helper)
        self.assertIn("pre_explicit_reboot=a0ac11c", launcher)
        self.assertIn("clean_root_boot=5577ebe", launcher)
        self.assertIn("clean_root_ownerless=fed71eb", launcher)
        self.assertIn("The one-shot clean root must remain recoverable", helper)
        self.assertIn("owner_uid=65534", helper)
        self.assertIn('selector=/run/ubuntu/.t630-next-root', helper)
        self.assertIn('consumed=/run/ubuntu/.t630-next-root.consumed', helper)
        self.assertLess(helper.index('test -z "$(grep " $root/"'),
                        helper.index('mv "$consumed" "$selector"'))
        self.assertLess(helper.index('mv "$consumed" "$selector"'),
                        helper.index('umount /run/ubuntu'))

    def test_screen_server_has_its_own_single_instance_lock(self):
        source = (ROOT / "ubuntu/t630_screen.py").read_text()
        self.assertIn("/run/t630-screen-service.lock", source)
        self.assertIn("fcntl.LOCK_EX | fcntl.LOCK_NB", source)
        self.assertIn("('127.0.0.1',8765)", source)

    def test_persistent_boot_has_non_systemd_remote_fallback(self):
        startup = (ROOT / "persistent/start-ubuntu").read_text()
        self.assertIn("TYPE,STATE", startup)
        self.assertIn("wifi:connected", startup)
        self.assertIn("/usr/local/sbin/t630-remote-start", startup)
        self.assertIn("/run/remote-start.log", startup)
        self.assertIn('attempt" -lt 60', startup)

    def test_live_view_tracks_the_real_output_transform(self):
        source = (ROOT / "ubuntu/t630_screen.py").read_text()
        self.assertIn("/run/t630-weston-rotation.state", source)
        self.assertIn("Image.Transpose.ROTATE_180", source)
        self.assertIn("Image.Transpose.ROTATE_270", source)


if __name__ == "__main__":
    unittest.main()
