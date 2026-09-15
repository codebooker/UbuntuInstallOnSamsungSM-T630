#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


SOURCE = Path(__file__).with_name("build_boot_persistent.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_boot_persistent", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


class PersistentBootTests(unittest.TestCase):
    def test_ramdisk_uses_current_startup_and_full_shutdown(self):
        self.assertEqual(
            builder.RAMDISK_FILES["bin/start-ubuntu"],
            builder.ROOT / "persistent/start-ubuntu")
        self.assertEqual(
            builder.RAMDISK_FILES["bin/stop-ubuntu"],
            builder.ROOT / "ubuntu/stop-ubuntu-remote")
        cpio_one, hashes_one = builder.ramdisk()
        cpio_two, hashes_two = builder.ramdisk()
        self.assertEqual(cpio_one, cpio_two)
        self.assertEqual(hashes_one, hashes_two)
        self.assertIn(b"wifi:connected", cpio_one)
        self.assertIn(b"t630-stock-vendor", cpio_one)
        self.assertIn(b'/bin/busybox "$action" -f', cpio_one)
        self.assertIn(b".t630-next-root", cpio_one)
        self.assertIn(b"/run/t630-selected-root", cpio_one)
        self.assertIn(b"/usr/local/share/t630/weston.ini", cpio_one)

    def test_clean_root_selector_is_fixed_consumed_and_recoverable(self):
        startup = (builder.ROOT / "persistent/start-ubuntu").read_text()
        self.assertIn("opt/t630/rehearsal/release-root", startup)
        self.assertIn('mv "$selector" "$consumed"', startup)
        self.assertLess(
            startup.index('mv "$selector" "$consumed"'),
            startup.index('root=$candidate'))
        self.assertIn("SM-T630 OFFLINE RELEASE ROOT", startup)
        self.assertIn("test ! -L \"$candidate\"", startup)

    def test_visible_terminal_is_recovery_only(self):
        startup = (builder.ROOT / "persistent/start-ubuntu").read_text()
        self.assertIn('! -f "$root/etc/t630/owner"', startup)
        self.assertIn('recovery-terminal.enabled', startup)
        self.assertIn('t630-recovery-terminal', startup)
        self.assertLess(startup.index('! -f "$root/etc/t630/owner"'),
                        startup.index('/usr/bin/weston-terminal'))

    def test_rehearsal_armer_is_identity_guarded(self):
        armer = builder.ROOT / "tools/arm_rehearsal_boot.sh"
        subprocess.run(["sh", "-n", armer], check=True)
        text = armer.read_text()
        self.assertIn("test ! -e \"$root/etc/t630/owner\"", text)
        self.assertIn("chroot \"$root\" /usr/bin/dpkg --audit", text)
        self.assertIn("T630_CLEAN_ROOT_ONE_SHOT_ARMED", text)

    def test_builder_pins_accepted_kernel_and_never_writes_a_device(self):
        text = SOURCE.read_text()
        self.assertIn(builder.KERNEL_SHA256, text)
        self.assertIn("OFFLINE_VALIDATED_ONLY_NOT_FLASH_APPROVED", text)
        self.assertIn('"retained_files": ["boot.img", "manifest.json"]', text)
        self.assertNotIn("/dev/sda19", text)
        self.assertNotIn("subprocess.run([\"dd\"", text)

    def test_guarded_writer_pins_current_candidate_and_neighbors(self):
        writer = SOURCE.with_name("write_release_boot_v1.sh")
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn("old_hash=5394a2347", text)
        self.assertIn("new_hash=1462fb6f", text)
        self.assertIn("PARTNAME=boot", text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)

    def test_v2_writer_accepts_only_v1_and_pins_one_shot_candidate(self):
        writer = SOURCE.with_name("write_release_boot_v2.sh")
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn("old_hash=1462fb6f", text)
        self.assertIn("new_hash=ce279665", text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)

    def test_v3_writer_accepts_only_v2_and_pins_ownerless_recovery(self):
        writer = SOURCE.with_name("write_release_boot_v3.sh")
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn("old_hash=ce279665", text)
        self.assertIn("new_hash=2d9ebe83", text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)

    def test_v4_writer_accepts_only_v3_and_pins_recovery_only_terminal(self):
        writer = SOURCE.with_name("write_release_boot_v4.sh")
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn("old_hash=2d9ebe83", text)
        self.assertIn("new_hash=368279fd", text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)

    def test_v5_writer_accepts_only_v4_and_pins_power_action_helper(self):
        writer = SOURCE.with_name("write_release_boot_v5.sh")
        subprocess.run(["sh", "-n", writer], check=True)
        text = writer.read_text()
        self.assertIn("old_hash=368279fd", text)
        self.assertIn("new_hash=d1f475dc", text)
        self.assertIn('dd if="$image" of=/dev/sda19', text)
        for partition in ("/dev/sda20", "/dev/sda21", "/dev/sda22", "/dev/sde19"):
            self.assertIn(partition, text)


if __name__ == "__main__":
    unittest.main()
