#!/usr/bin/python3
"""Touch-friendly confirmation for the guarded Ubuntu-to-Android switch."""

import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


COMMAND = [
    "/usr/bin/sudo",
    "-n",
    "/usr/local/sbin/t630-switch-to-native-android",
    "--switch-and-reboot",
]


class SwitchDialog(Gtk.Window):
    def __init__(self):
        super().__init__(title="Restart into Android")
        self.set_default_size(680, 360)
        self.set_border_width(32)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("destroy", Gtk.main_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.add(box)
        heading = Gtk.Label(label="Restart into Android?", xalign=0)
        heading.get_style_context().add_class("title")
        box.pack_start(heading, False, False, 0)
        explanation = Gtk.Label(
            label=(
                "Open Ubuntu apps will close. Your Ubuntu files remain on their own "
                "partition, and Android will use its encrypted data partition."
            ),
            xalign=0,
        )
        explanation.set_line_wrap(True)
        box.pack_start(explanation, False, False, 0)
        self.status = Gtk.Label(
            label="The tablet verifies every protected partition before changing BOOT.",
            xalign=0,
        )
        self.status.set_line_wrap(True)
        box.pack_start(self.status, False, False, 0)

        actions = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        actions.set_layout(Gtk.ButtonBoxStyle.END)
        actions.set_spacing(18)
        box.pack_end(actions, False, False, 0)
        self.cancel = Gtk.Button(label="Cancel")
        self.cancel.connect("clicked", lambda _button: self.close())
        actions.add(self.cancel)
        self.restart = Gtk.Button(label="Restart into Android")
        self.restart.get_style_context().add_class("suggested-action")
        self.restart.connect("clicked", self.begin)
        actions.add(self.restart)

        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property("gtk-application-prefer-dark-theme", True)

    def begin(self, _button):
        self.cancel.set_sensitive(False)
        self.restart.set_sensitive(False)
        self.status.set_text("Verifying the tablet and preparing Android…")
        try:
            process = subprocess.Popen(
                COMMAND,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as error:
            self.failed(str(error))
            return
        threading.Thread(target=self.wait_for_switch, args=(process,), daemon=True).start()

    def wait_for_switch(self, process):
        stdout, stderr = process.communicate()
        GLib.idle_add(self.finished, process.returncode, stdout, stderr)

    def finished(self, returncode, stdout, stderr):
        if returncode == 0:
            self.status.set_text("Android verified. Restarting now…")
            return False
        message = (stderr or stdout or "The guarded switch was refused.").strip().splitlines()[-1]
        self.failed(message)
        return False

    def failed(self, message):
        self.status.set_text(f"Could not switch safely: {message}")
        self.cancel.set_sensitive(True)
        self.restart.set_sensitive(True)


if __name__ == "__main__":
    window = SwitchDialog()
    window.show_all()
    Gtk.main()
