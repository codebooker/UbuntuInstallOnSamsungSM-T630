#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
UBUNTU = ROOT / "ubuntu"
sys.path.insert(0, str(UBUNTU))
SPEC = importlib.util.spec_from_file_location(
    "t630_install_owner_assets", UBUNTU / "t630-install-owner-assets.py"
)
assets = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(assets)


class OwnerAssetsTests(unittest.TestCase):
    def test_empty_typed_gsettings_array_is_valid(self):
        self.assertEqual(assets.parse_enabled_extensions("@as []\n"), [])

    def source(self, root):
        source = root / "source"
        (source / "schemas").mkdir(parents=True)
        (source / "extension.js").write_text("extension\n")
        (source / "metadata.json").write_text("{}\n")
        (source / "schemas/org.gnome.shell.extensions.t630-tablet-tools.gschema.xml").write_text(
            "<schemalist/>\n"
        )
        return source

    def config_source(self, root):
        source = root / "owner-config"
        for relative in assets.CONFIG_FILES:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"config {relative.name}\n")
        return source

    def test_digest_rejects_symlinked_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            (root / "outside").write_text("bad")
            (source / "extension.js").unlink()
            (source / "extension.js").symlink_to(root / "outside")
            with self.assertRaises(RuntimeError):
                assets.source_digest(source)

    def test_install_compiles_atomically_and_preserves_other_extensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            data = root / "data"
            config_source = self.config_source(root)
            config_home = root / "config"
            owner = types.SimpleNamespace(uid=1234)
            gets = types.SimpleNamespace(returncode=0, stdout="['other@example']\n")
            compiled = types.SimpleNamespace(returncode=0, stdout="")
            with mock.patch.object(assets, "resolve_owner", return_value=owner), \
                    mock.patch.object(assets.os, "geteuid", return_value=1234), \
                    mock.patch.object(assets.subprocess, "run", side_effect=[compiled, gets, compiled]) as run:
                assets.install(source, data, config_source, config_home)
            target = data / "gnome-shell/extensions" / assets.EXTENSION_ID
            self.assertEqual((target / "extension.js").read_text(), "extension\n")
            self.assertTrue((target / ".t630-source-sha256").is_file())
            self.assertIn("other@example", run.call_args_list[-1].args[0][-1])
            self.assertIn(assets.EXTENSION_ID, run.call_args_list[-1].args[0][-1])
            for relative in assets.CONFIG_FILES:
                self.assertEqual((config_home / relative).read_bytes(),
                                 (config_source / relative).read_bytes())

    def test_matching_digest_skips_recompile_but_enables_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.source(root)
            data = root / "data"
            target = data / "gnome-shell/extensions" / assets.EXTENSION_ID
            target.mkdir(parents=True)
            (target / ".t630-source-sha256").write_text(assets.source_digest(source) + "\n")
            owner = types.SimpleNamespace(uid=1234)
            gets = types.SimpleNamespace(returncode=0, stdout=f"['{assets.EXTENSION_ID}']\n")
            with mock.patch.object(assets, "resolve_owner", return_value=owner), \
                    mock.patch.object(assets.os, "geteuid", return_value=1234), \
                    mock.patch.object(assets.subprocess, "run", return_value=gets) as run:
                assets.install(source, data, root / "absent-config", root / "config")
            self.assertEqual(run.call_count, 1)

    def test_owner_config_rejects_symlink_without_touching_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.config_source(root)
            first = source / assets.CONFIG_FILES[0]
            first.unlink()
            (root / "outside").write_text("unsafe")
            first.symlink_to(root / "outside")
            with self.assertRaises(RuntimeError):
                assets.install_owner_configs(source, root / "config")
            self.assertFalse((root / "config" / assets.CONFIG_FILES[0]).exists())


if __name__ == "__main__":
    unittest.main()
