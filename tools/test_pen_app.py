import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / 'ubuntu/t630-pen-app.py'
spec = importlib.util.spec_from_file_location('pen_app', SOURCE)
pen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pen)
metadata_spec = importlib.util.spec_from_file_location(
    'pen_metadata', SOURCE.with_name('t630-pen-x11-metadata.py'))
metadata = importlib.util.module_from_spec(metadata_spec)
metadata_spec.loader.exec_module(metadata)


class PenAppTests(unittest.TestCase):
    def test_serial_metadata_is_published_after_device_refresh(self):
        text = '\n'.join(f'xwayland-tablet {kind}:14 id={device}' for
                         kind, device in (('stylus', 8), ('eraser', 9), ('cursor', 10)))
        calls = []
        def run(argv, **_kwargs):
            calls.append(argv)
            return SimpleNamespace(stdout=text if argv[1:] == ['--list', '--short'] else 'Abs Pressure')
        with patch.object(metadata.sys, 'argv', ['metadata', '--refresh']), \
             patch.dict(metadata.os.environ, {'DISPLAY': ':3'}), \
             patch.object(metadata, 'pen_is_idle', return_value=True), \
             patch.object(metadata.subprocess, 'run', side_effect=run):
            metadata.main()
        for device in (8, 9, 10):
            enable = next(i for i, command in enumerate(calls) if command[1:] == ['enable', str(device)])
            serial = next(i for i, command in enumerate(calls) if 'Wacom Serial IDs' in command and
                          command[4] == str(device))
            self.assertLess(enable, serial)

    def test_active_pen_refuses_refresh_before_xinput(self):
        with patch.object(metadata.sys, 'argv', ['metadata', '--refresh']), \
             patch.dict(metadata.os.environ, {'DISPLAY': ':3'}), \
             patch.object(metadata, 'pen_is_idle', return_value=False), \
             patch.object(metadata.subprocess, 'run') as run:
            with self.assertRaises(SystemExit):
                metadata.main()
            run.assert_not_called()

    def test_metadata_targets_only_complete_private_tablet_set(self):
        text = '\n'.join(f' ↳ xwayland-tablet {kind}:14\tid={device} [slave pointer]' for
                         kind, device in (('stylus', 8), ('eraser', 9), ('cursor', 10)))
        devices = metadata.tablet_devices(text + '\n ↳ keyboard id=6')
        self.assertEqual([device for _, _, device in devices], [8, 9, 10])
        for invalid in ('keyboard id=6', text + '\n' + text, text.replace('cursor', 'mouse')):
            with self.assertRaises(ValueError):
                metadata.tablet_devices(invalid)

    def test_native_apps_keep_session_and_file_arguments(self):
        for kind, command in pen.COMMANDS.items():
            with self.subTest(kind=kind), patch.object(pen.os, 'getuid', return_value=1000), \
                 patch.object(pen.sys, 'argv', ['t630-pen-app', kind, '/home/owner/My Drawing.ora']), \
                 patch.dict(pen.os.environ, {'WAYLAND_DISPLAY': 't630-gnome-0',
                            'XDG_CONFIG_HOME': '/home/owner/.config/profile'}, clear=True), \
                 patch.object(pen.os, 'execve') as execute:
                pen.main()
                binary, argv, env = execute.call_args.args
                self.assertEqual(binary, command)
                self.assertEqual(argv, [command, '/home/owner/My Drawing.ora'])
                self.assertEqual(env['GDK_BACKEND'], 'wayland')
                self.assertEqual(env['GTK_THEME'], 'Adwaita:dark')
                self.assertEqual(env['XDG_CONFIG_HOME'], '/home/owner/.config/profile')
                self.assertNotIn('LD_PRELOAD', env)

    def test_root_and_wrong_display_refused(self):
        with patch.object(pen.os, 'getuid', return_value=0):
            with self.assertRaises(SystemExit):
                pen.main()
        with patch.object(pen.os, 'getuid', return_value=1000), \
             patch.object(pen.sys, 'argv', ['t630-pen-app', 'notes']), \
             patch.dict(pen.os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}, clear=True):
            with self.assertRaises(SystemExit):
                pen.main()

    def test_unknown_app_refused(self):
        with patch.object(pen.os, 'getuid', return_value=1000), \
             patch.object(pen.sys, 'argv', ['t630-pen-app', 'shell']):
            with self.assertRaises(SystemExit):
                pen.main()


if __name__ == '__main__':
    unittest.main()
