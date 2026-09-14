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
        self.assertIn(b"/bin/busybox reboot -f", cpio_one)

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


if __name__ == "__main__":
    unittest.main()
