#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / 'ubuntu/t630-audio-session-cleanup.py'
if not source.exists():
    source = Path('/usr/local/share/t630/t630-audio-session-cleanup.py')
spec = importlib.util.spec_from_file_location('audio_cleanup', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.env = {b'XDG_CONFIG_HOME': b'/home/tablet/.config/t630-gnome-preview',
                    b'XDG_RUNTIME_DIR': b'/run/user/1000'}

    def test_known_profile_servers_match(self):
        for name in ('pipewire', 'pipewire-pulse', 'wireplumber'):
            self.assertTrue(module.matches(1000, '/usr/bin/' + name, name, self.env))

    def test_other_user_is_untouched(self):
        self.assertFalse(module.matches(0, '/usr/bin/pipewire', 'pipewire', self.env))

    def test_test_profile_is_untouched(self):
        self.env[b'XDG_CONFIG_HOME'] = b'/tmp/t630-render-test-private/config'
        self.assertFalse(module.matches(1000, '/usr/bin/pipewire', 'pipewire', self.env))

    def test_unknown_binary_is_untouched(self):
        self.assertFalse(module.matches(1000, '/usr/bin/gnome-shell', 'pipewire', self.env))

    def test_missing_runtime_is_untouched(self):
        del self.env[b'XDG_RUNTIME_DIR']
        self.assertFalse(module.matches(1000, '/usr/bin/pipewire', 'pipewire', self.env))


if __name__ == '__main__':
    unittest.main()
