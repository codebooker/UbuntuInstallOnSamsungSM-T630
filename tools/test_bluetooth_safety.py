#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class BluetoothSafetyTests(unittest.TestCase):
    def test_launcher_is_valid_shell_and_has_bounded_retries(self):
        launcher = ROOT / "ubuntu/t630-bluetooth-start"
        subprocess.run(["sh", "-n", launcher], check=True)
        text = launcher.read_text()
        self.assertIn('while [ "$loader_attempt" -le 3 ]', text)
        self.assertIn("failed after 3 attempts", text)

    def test_timer_backport_drains_before_and_after_workqueue(self):
        patch = (
            ROOT
            / "patches/0008-bluetooth-qca-synchronize-ibs-timers-on-close.patch"
        ).read_text()
        destroy = patch.index("+\tdestroy_workqueue(qca->workqueue);")
        deletes = [
            index
            for index in range(len(patch))
            if patch.startswith("+\tdel_timer_sync(&qca->wake_retrans_timer);", index)
        ]
        self.assertEqual(len(deletes), 2)
        self.assertLess(deletes[0], destroy)
        self.assertGreater(deletes[1], destroy)

    def test_supervisor_is_bounded_and_desktop_uses_it(self):
        supervisor = ROOT / "ubuntu/t630-bluetooth-supervisor"
        subprocess.run(["sh", "-n", supervisor], check=True)
        text = supervisor.read_text()
        self.assertIn("flock -n 9", text)
        self.assertIn('if [ "$delay" -gt 30 ]', text)
        self.assertIn("/run/t630-stopping", text)
        desktop = (ROOT / "ubuntu/t630-desktop-autostart").read_text()
        self.assertIn("/usr/local/sbin/t630-bluetooth-supervisor", desktop)

    def test_managed_session_reaps_inherited_service_children(self):
        managed = (ROOT / "ubuntu/t630-managed-session.py").read_text()
        self.assertIn("os.waitpid(-1, 0)", managed)
        self.assertIn("if reaped_pid == pid:", managed)

    def test_health_check_avoids_recursive_sysfs_reads(self):
        health = ROOT / "tools/check_runtime_health.sh"
        subprocess.run(["sh", "-n", health], check=True)
        text = health.read_text()
        self.assertNotIn("find /sys", text)
        self.assertNotIn("/sys/**", text)

    def test_v8_writer_pins_source_target_and_protected_partitions(self):
        writer = ROOT / "tools/write_bluetooth_qca_close_sync_boot_v8.sh"
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn(
            "old_hash=c9fd8a0025e2c8acc8c7781a077c2af71eb49c01688cf9ae010a4bc8c15118db",
            text,
        )
        self.assertIn(
            "new_hash=2bfa801e391476fb9e4f597d31846fc2113b8c0c761130caa4a7fef4dec1876a",
            text,
        )
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)
        self.assertIn("/sys/class/power_supply/ac/online", text)
        self.assertIn("/sys/class/power_supply/usb/online", text)


if __name__ == "__main__":
    unittest.main()
