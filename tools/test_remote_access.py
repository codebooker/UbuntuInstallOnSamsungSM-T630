#!/usr/bin/env python3

import subprocess
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('remote_install', ROOT / 'ubuntu/install-remote-access.py')
remote_install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote_install)


class RemoteAccessTests(unittest.TestCase):
    def test_owner_access_policy_is_key_only_and_screen_tunnel_only(self):
        config = remote_install.make_config('new_owner')
        for required in ('AllowUsers new_owner', 'PermitRootLogin no',
                         'PasswordAuthentication no', 'AuthenticationMethods publickey',
                         'AllowTcpForwarding local', 'PermitOpen 127.0.0.1:8765',
                         'AllowAgentForwarding no', 'X11Forwarding no'):
            self.assertIn(required, config)
        with self.assertRaises(ValueError):
            remote_install.make_config('owner\nPermitRootLogin yes')

    def test_public_key_input_rejects_private_keys_options_and_multiple_keys(self):
        key = 'ssh-ed25519 AAAAB3NzaTest example'
        self.assertEqual(remote_install.validate_public_key(key), key + '\n')
        for text in ('-----BEGIN OPENSSH PRIVATE KEY-----', 'command="sh" ' + key,
                     key + '\n' + key, 'ssh-rsa AAAA'):
            with self.assertRaises(ValueError):
                remote_install.validate_public_key(text)

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
        self.assertIn("cold_boot_journal=0341f64e", launcher)
        self.assertIn("cold_boot_journal_fixed=7e27393b", launcher)
        self.assertIn("The one-shot clean root must remain recoverable", helper)
        self.assertIn("owner_uid=65534", helper)
        self.assertIn('selector=/run/ubuntu/.t630-next-root', helper)
        self.assertIn('consumed=/run/ubuntu/.t630-next-root.consumed', helper)
        self.assertLess(helper.index('test -z "$(grep " $root/"'),
                        helper.index('mv "$consumed" "$selector"'))
        self.assertLess(helper.index('mv "$consumed" "$selector"'),
                        helper.index('umount /run/ubuntu'))
        self.assertIn('journal=/run/ubuntu/.t630-last-system-action', helper)
        self.assertIn('system_action_stage starting', helper)
        self.assertIn('system_action_stage ready-to-unmount', helper)
        self.assertIn("/usr/bin/lxc-info", helper)
        self.assertIn("/usr/bin/lxc-stop", helper)
        self.assertIn("/var/lib/waydroid/rootfs/vendor/waydroid.prop", helper)
        self.assertIn("/sys/fs/cgroup/cpu_cpuacct", helper)
        self.assertIn("/dev/binderfs", helper)
        self.assertLess(helper.index("/var/lib/waydroid/rootfs/vendor/waydroid.prop"),
                        helper.index("/mnt/stock-vendor-full/lib64/hw"))
        self.assertIn('system_action_stage() {\n    stage=$1\n    (', helper)
        self.assertLess(helper.index('system_action_stage ready-to-unmount'),
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
