#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ChromeOskTests(unittest.TestCase):
    def test_watcher_is_scoped_to_chrome_editable_focus(self):
        source = (ROOT / "ubuntu/t630-chrome-osk.py").read_text()
        self.assertIn('CHROME_APPLICATIONS = frozenset(("Google Chrome", "Chromium"))', source)
        self.assertIn('Atspi.StateType.EDITABLE', source)
        self.assertIn('Atspi.Collection.get_matches', source)
        self.assertIn('GLib.timeout_add(400, self._poll_focus)', source)
        self.assertIn('object:state-changed:focused', source)
        self.assertIn('never deduplicate this call', source)
        self.assertIn('self.requested_visible = True\n            self._call_shell("ShowKeyboard")', source)
        self.assertIn('self._call_shell("ShowKeyboard")', source)
        self.assertNotIn('self._call_shell("HideKeyboard")', source)

    def test_shell_exports_private_keyboard_methods(self):
        extension = (ROOT / "ubuntu/gnome-tablet-tools/extension.js").read_text()
        self.assertIn('/org/gnome/Shell/Extensions/T630TabletTools', extension)
        self.assertIn('org.gnome.Shell.Extensions.T630TabletTools', extension)
        self.assertIn('method name="GetKeyboardVisible"', extension)
        self.assertIn('this._keyboardDbus?.unexport()', extension)


if __name__ == "__main__":
    unittest.main()
