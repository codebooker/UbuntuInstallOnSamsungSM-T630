#!/usr/bin/python3
"""Touch-friendly live rear-camera color control for the SM-T630."""

import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402


SETTINGS = Path.home() / ".config" / "t630-camera" / "rear-color"


def read_setting():
    try:
        value = int(SETTINGS.read_text().strip())
        return max(-100, min(100, value))
    except (OSError, ValueError):
        return 0


class ColorWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Rear Camera Color")
        self.set_default_size(720, 250)
        self.pending_save = 0

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(32)
        content.set_margin_end(32)
        self.set_child(content)

        heading = Gtk.Label(label="Rear camera color")
        heading.add_css_class("title-1")
        content.append(heading)

        hint = Gtk.Label(label="Move toward Cooler until whites look neutral. Changes apply live.")
        hint.set_wrap(True)
        content.append(hint)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -100, 100, 1)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(False)
        self.scale.add_mark(-100, Gtk.PositionType.BOTTOM, "Warmer")
        self.scale.add_mark(0, Gtk.PositionType.BOTTOM, "Current")
        self.scale.add_mark(100, Gtk.PositionType.BOTTOM, "Cooler")
        self.scale.set_value(read_setting())
        self.scale.connect("value-changed", self.changed)
        content.append(self.scale)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        buttons.set_halign(Gtk.Align.CENTER)
        reset = Gtk.Button(label="Reset to current profile")
        reset.connect("clicked", lambda _button: self.scale.set_value(0))
        buttons.append(reset)
        close = Gtk.Button(label="Done")
        close.add_css_class("suggested-action")
        close.connect("clicked", lambda _button: self.close())
        buttons.append(close)
        content.append(buttons)

    def changed(self, _scale):
        if self.pending_save:
            GLib.source_remove(self.pending_save)
        self.pending_save = GLib.timeout_add(80, self.save)

    def save(self):
        value = int(round(self.scale.get_value()))
        SETTINGS.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = SETTINGS.with_suffix(".new")
        temporary.write_text(f"{value}\n")
        os.chmod(temporary, 0o644)
        os.replace(temporary, SETTINGS)
        self.pending_save = 0
        return GLib.SOURCE_REMOVE


class ColorApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.t630.CameraColor",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.props.active_window or ColorWindow(self)
        window.present()


if __name__ == "__main__":
    raise SystemExit(ColorApplication().run())
