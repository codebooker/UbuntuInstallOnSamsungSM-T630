import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('app_grid',
    Path(__file__).resolve().parents[1] / 'ubuntu/t630-app-grid.py')
grid = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grid)


class Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})
    def get_strv(self, key):
        return list(self.values.get(key, []))
    def get_user_value(self, key):
        return self.values.get(key)
    def set_strv(self, key, value):
        self.values[key] = list(value)
    def set_string(self, key, value):
        self.values[key] = value
    def set_boolean(self, key, value):
        self.values[key] = value


class AppGridTests(unittest.TestCase):
    def setup_settings(self, children, favorites=None):
        settings = {'org.gnome.desktop.app-folders': Settings({'folder-children': children}),
                    'org.gnome.desktop.app-folders.folder': Settings(),
                    'org.gnome.shell': Settings(favorites)}
        def factory(schema_id, **_kwargs):
            return settings[schema_id]
        return settings, factory

    def test_defaults_are_flattened_and_empty_sentinel_prevents_recreation(self):
        settings, factory = self.setup_settings(['Utilities', 'YaST', 'Pardus'])
        grid.apply(factory)
        self.assertEqual(settings['org.gnome.desktop.app-folders'].get_strv('folder-children'),
                         [grid.SENTINEL])
        empty = settings['org.gnome.desktop.app-folders.folder']
        for key in ('apps', 'categories', 'excluded-apps'):
            self.assertEqual(empty.get_strv(key), [])
        self.assertEqual(settings['org.gnome.shell'].get_strv('favorite-apps'), grid.DEFAULT_FAVORITES)

    def test_personal_folders_and_favorites_survive_repeated_application(self):
        settings, factory = self.setup_settings(['custom-notes', 'Utilities'],
                                               {'favorite-apps': ['xournalpp.desktop']})
        for _ in range(3):
            grid.apply(factory, pin_drawing=True)
        self.assertEqual(settings['org.gnome.desktop.app-folders'].get_strv('folder-children'),
                         ['custom-notes', grid.SENTINEL])
        self.assertEqual(settings['org.gnome.shell'].get_strv('favorite-apps'),
                         ['xournalpp.desktop', 'mypaint.desktop'])

    def test_intentionally_empty_favorites_are_not_reset(self):
        settings, factory = self.setup_settings([], {'favorite-apps': []})
        grid.apply(factory)
        self.assertEqual(settings['org.gnome.shell'].get_strv('favorite-apps'), [])

    def test_drawing_launcher_is_named_and_still_native(self):
        desktop = (Path(__file__).resolve().parents[1] / 'ubuntu/t630-mypaint.desktop').read_text()
        self.assertIn('Name=MyPaint Drawing\n', desktop)
        self.assertIn('t630-pen-app drawing %F', desktop)


if __name__ == '__main__':
    unittest.main()
