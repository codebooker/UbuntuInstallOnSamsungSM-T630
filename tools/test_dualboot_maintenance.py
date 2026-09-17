#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DualbootMaintenanceTest(unittest.TestCase):
    def test_shell_sources_parse(self):
        for source in (
            "maintenance/init", "maintenance/usb-shell",
            "maintenance/dualboot-preflight", "maintenance/restore-ubuntu-boot",
        ):
            subprocess.run(["sh", "-n", ROOT / source], check=True)

    def test_init_does_not_mount_a_block_device(self):
        text = (ROOT / "maintenance/init").read_text()
        self.assertNotIn("/dev/sda", text)
        self.assertNotIn("/dev/sde", text)
        self.assertNotIn("dualboot-preflight &", text)

    def test_preflight_has_no_apply_path(self):
        text = (ROOT / "maintenance/dualboot-preflight").read_text()
        self.assertNotIn("--apply", text)
        self.assertNotIn("sgdisk --delete", text)
        self.assertNotIn("sgdisk --new", text)
        self.assertNotIn("resize2fs /dev", text)
        self.assertIn("e2fsck -fn", text)
        self.assertIn("sgdisk --verify", text)

    def test_restore_is_exact_boot_only_and_needs_token(self):
        text = (ROOT / "maintenance/restore-ubuntu-boot").read_text()
        self.assertIn("/dev/sda19", text)
        self.assertNotIn("/dev/sda34", text)
        self.assertNotIn("/dev/sda35", text)
        self.assertIn("RESTORE EXACT SM-T630 UBUNTU BOOT", text)
        self.assertIn("BOOT readback mismatch", text)
        self.assertIn("reboot_manually", text.lower())

    def test_builder_pins_every_private_input(self):
        text = (ROOT / "tools/build_dualboot_maintenance.py").read_text()
        self.assertIn("MAINTENANCE_HASHES", text)
        self.assertIn("OFFLINE_VALIDATED_PREFLIGHT_WITH_PINNED_BOOT_RESTORE_NOT_FLASH_APPROVED", text)
        self.assertIn("refusing to overwrite existing output", text)
        self.assertIn("maintenance input hash mismatch", text)

    def test_stager_is_boot_only_with_rollback(self):
        source = ROOT / "tools/stage_dualboot_maintenance_v4.sh"
        subprocess.run(["sh", "-n", source], check=True)
        text = source.read_text()
        self.assertIn("/dev/sda19", text)
        self.assertNotIn("/dev/sda34", text)
        self.assertNotIn("/dev/sda35", text)
        self.assertIn("rollback_on_error", text)
        self.assertIn("check_neighbors", text)
        self.assertIn("READBACK_VERIFIED", text)

    def test_serial_transport_discovers_maintenance_console(self):
        text = (ROOT / "tools/serial_link.py").read_text()
        self.assertIn("usbmodemT630MAINT001", text)
        self.assertIn("usbmodemT630BRINGUP001", text)
        self.assertIn("Expected one SM-T630 serial console", text)

    def test_sparse_rehearsal_is_file_only_and_exact(self):
        source = ROOT / "tools/test_dualboot_layout_docker.sh"
        subprocess.run(["sh", "-n", source], check=True)
        text = source.read_text()
        self.assertIn("t630-dualboot-rehearsal.img", text)
        self.assertIn("--sector-size 4096", text)
        self.assertIn("16777216", text)
        self.assertIn("2735104:19512319", text)
        self.assertIn("19512320:31099898", text)
        self.assertIn("--load-backup=/work/gpt-before-split.bin", text)
        self.assertNotIn("/dev/sda", text)
        self.assertNotIn("/dev/sde", text)

    def test_persistent_boot_accepts_only_two_exact_root_layouts(self):
        text = (ROOT / "persistent/start-ubuntu").read_text()
        self.assertIn("userdata:226918360|linuxroot:134217728", text)
        self.assertIn("/dev/sda34", text)
        self.assertIn("64de854453ea4fdc8946d6b07e238630", text)
        self.assertNotIn("/dev/sda35", text)

    def test_dual_layout_builder_is_offline_and_pinned(self):
        source = ROOT / "tools/build_dual_layout_boot.py"
        subprocess.run(["python3", "-m", "py_compile", source], check=True)
        text = source.read_text()
        self.assertIn("OFFLINE_VALIDATED_DUAL_LAYOUT_NOT_FLASH_APPROVED", text)
        self.assertIn("linuxroot", text)
        self.assertIn("134217728", text)
        self.assertNotIn("/dev/sda19", text)

    def test_dual_layout_stager_is_boot_only(self):
        source = ROOT / "tools/stage_dual_layout_boot_v1.sh"
        subprocess.run(["sh", "-n", source], check=True)
        text = source.read_text()
        self.assertIn("/dev/sda19", text)
        self.assertNotIn("/dev/sda34", text)
        self.assertNotIn("/dev/sda35", text)
        self.assertIn("rollback_on_error", text)
        self.assertIn("READBACK_VERIFIED", text)


if __name__ == "__main__":
    unittest.main()
