#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SOURCE = Path(__file__).with_name("build_stock_assets_deb.py")
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("build_stock_assets_deb", SOURCE)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


class StockAssetsPackageTests(unittest.TestCase):
    def source(self, root):
        source = root / "source"
        (source / "input/tree/subdir").mkdir(parents=True)
        (source / "input/tree/subdir/firmware.bin").write_bytes(b"firmware")
        (source / "input/one.conf").write_text("config\n", encoding="utf-8")
        return source

    def ar_members(self, package):
        offset = 8
        result = {}
        while offset < len(package):
            header = package[offset:offset + 60]
            name = header[:16].decode().strip().rstrip("/")
            size = int(header[48:58].decode().strip())
            start = offset + 60
            result[name] = package[start:start + size]
            offset = start + size + (size % 2)
        return result

    def test_reproducible_private_package_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            maps = {"input/tree": "opt/t630/vendor/firmware"}
            files = {"input/one.conf": "opt/t630/vendor/etc/one.conf"}
            one, two = root / "one.deb", root / "two.deb"
            first = builder.build(source, one, 1700000000, {}, maps, files, frozenset())
            second = builder.build(source, two, 1700000000, {}, maps, files, frozenset())
            self.assertEqual(first, second)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            members = self.ar_members(one.read_bytes())
            data = root / "data.tar.xz"
            data.write_bytes(members["data.tar.xz"])
            with tarfile.open(data, "r:xz") as archive:
                names = {item.name.removeprefix("./") for item in archive.getmembers()}
                manifest = archive.extractfile(
                    "./usr/share/doc/t630-stock-assets/source-manifest.json").read()
            self.assertIn("opt/t630/vendor/firmware/subdir/firmware.bin", names)
            self.assertIn(b'"sha256"', manifest)
            self.assertNotIn("home", names)

    def test_wrong_baseline_and_escaping_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            with self.assertRaises(ValueError):
                builder.validate_critical(source, {"input/one.conf": "0" * 64})
            link = source / "input/tree/escape"
            link.symlink_to("../../../../outside")
            with self.assertRaises(ValueError):
                builder.collect(source, {"input/tree": "opt/t630/vendor"}, {}, frozenset())

    def test_release_map_excludes_mutable_and_identity_state(self):
        selected = "\n".join(builder.TREE_MAP) + "\n" + "\n".join(builder.FILE_MAP)
        for forbidden in (
            "/home", "system-connections", "t630-bluetooth/address",
            "sensors/registry", "sec_efs", "machine-id",
        ):
            self.assertNotIn(forbidden, selected)
        self.assertIn("opt/t630/vendor/firmware/wlan/qca_cld/wlan_mac.bin",
                      builder.EXCLUDED_SOURCE_PATHS)

    def test_symlinked_source_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            link = root / "source-link"
            link.symlink_to(source, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "real directory"):
                builder.collect(link, {}, {}, frozenset())


if __name__ == "__main__":
    unittest.main()
