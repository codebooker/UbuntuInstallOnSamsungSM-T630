#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "ubuntu/t630-chrome-ime.py"
SPEC = importlib.util.spec_from_file_location("t630_chrome_ime", SOURCE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class ChromeImeTests(unittest.TestCase):
    def test_patches_all_launcher_actions_once(self):
        source = """[Desktop Entry]\nExec=/usr/bin/google-chrome-stable %U\n[Desktop Action new-window]\nExec=/usr/bin/google-chrome-stable\n"""
        once = module.patched_launcher(source)
        twice = module.patched_launcher(once.removeprefix(module.MARKER))
        self.assertEqual(once, twice)
        self.assertEqual(once.count("--enable-wayland-ime"), 2)
        self.assertEqual(once.count("--wayland-text-input-version=3"), 2)
        self.assertIn(
            "Exec=/usr/bin/google-chrome-stable --enable-wayland-ime "
            "--wayland-text-input-version=3 %U",
            once,
        )

    def test_does_not_touch_unrelated_exec(self):
        source = "Exec=/usr/bin/firefox %U\nExec=/usr/bin/env google-chrome %U\n"
        self.assertEqual(module.patched_launcher(source), module.MARKER + source)


if __name__ == "__main__":
    unittest.main()
