from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SpiNameSafetyTests(unittest.TestCase):
    def test_patch_guards_unbound_spi_devices_before_conversion(self):
        patch = (ROOT / "patches/0018-spi-name-handle-unbound-device.patch").read_text()
        guard = '+\tif (!spi->dev.driver)'
        conversion = '+\tsdrv = to_spi_driver(spi->dev.driver);'
        self.assertIn(guard, patch)
        self.assertIn(conversion, patch)
        self.assertLess(patch.index(guard), patch.index(conversion))

    def test_runtime_tools_do_not_glob_sysfs_name_attributes(self):
        forbidden = (
            "find /sys",
            "/sys/bus/spi/devices/*/name",
            "/sys/bus/i2c/devices/*/name",
        )
        for path in list((ROOT / "tools").glob("*.py")) + list(
            (ROOT / "tools").glob("*.sh")
        ):
            if path.name.startswith("test_"):
                continue
            text = path.read_text(errors="replace")
            for pattern in forbidden:
                self.assertNotIn(pattern, text, f"unsafe sysfs discovery in {path}")


if __name__ == "__main__":
    unittest.main()
