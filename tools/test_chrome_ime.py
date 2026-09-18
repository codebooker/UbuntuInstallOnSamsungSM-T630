#!/usr/bin/env python3

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


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
        self.assertEqual(once.count("--force-renderer-accessibility=on-screen"), 2)
        self.assertEqual(once.count("--enable-features=AccessibilityOnScreenAXMode"), 2)
        self.assertIn(
            "Exec=/usr/bin/google-chrome-stable --enable-wayland-ime "
            "--wayland-text-input-version=3 "
            "--force-renderer-accessibility=on-screen "
            "--enable-features=AccessibilityOnScreenAXMode %U",
            once,
        )

    def test_does_not_touch_unrelated_exec(self):
        source = "Exec=/usr/bin/firefox %U\nExec=/usr/bin/env google-chrome %U\n"
        self.assertEqual(module.patched_launcher(source), module.MARKER + source)

    def test_synchronizer_is_idempotent_and_handles_late_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "google-chrome.desktop"
            with mock.patch.object(module, "SOURCE", source), mock.patch.dict(
                os.environ, {"XDG_DATA_HOME": str(root / "data")}
            ):
                module.synchronize_launcher()
                target = root / "data/applications/google-chrome.desktop"
                self.assertFalse(target.exists())
                source.write_text("Exec=/usr/bin/google-chrome-stable %U\n")
                module.synchronize_launcher()
                first_mtime = target.stat().st_mtime_ns
                module.synchronize_launcher()
                self.assertEqual(target.stat().st_mtime_ns, first_mtime)
                self.assertIn("--force-renderer-accessibility=on-screen", target.read_text())
                source.unlink()
                module.synchronize_launcher()
                self.assertFalse(target.exists())

    def test_finds_only_own_incompatible_main_process(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)

            def process(pid, uid, arguments):
                path = proc / str(pid)
                path.mkdir()
                (path / "status").write_text(f"Name:\tchrome\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n")
                (path / "cmdline").write_bytes(b"\0".join(a.encode() for a in arguments) + b"\0")

            own = os.getuid()
            process(10, own, [module.CHROME_BINARY])
            process(11, own, [module.CHROME_BINARY, *module.FLAGS])
            process(12, own, [module.CHROME_BINARY, "--type=renderer"])
            process(13, own + 1, [module.CHROME_BINARY])
            self.assertEqual(module.incompatible_chrome_pids(proc), [10])

    def test_compatible_relaunch_is_detached_and_exact(self):
        with mock.patch.object(module.subprocess, "Popen") as popen:
            module.launch_compatible_chrome()
        popen.assert_called_once_with(
            ["/usr/bin/google-chrome-stable", *module.FLAGS],
            stdin=module.subprocess.DEVNULL,
            stdout=module.subprocess.DEVNULL,
            stderr=module.subprocess.DEVNULL,
            start_new_session=True,
        )

    def test_watch_mode_is_available(self):
        source = SOURCE.read_text()
        self.assertIn('["--watch"]', source)
        self.assertIn("signal.SIGTERM", source)
        session = (SOURCE.parents[1] / "ubuntu/t630-gnome-session").read_text()
        self.assertIn("t630-chrome-ime --watch", session)
        self.assertIn('kill -TERM "$chrome_ime_pid"', session)


if __name__ == "__main__":
    unittest.main()
