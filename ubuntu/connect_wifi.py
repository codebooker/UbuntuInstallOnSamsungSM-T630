#!/usr/bin/python3
"""Local touch-friendly password entry. Never log or pass the secret in argv."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import threading
from pathlib import Path
import os

def primary_wifi():
    for device in Path('/sys/class/net').iterdir():
        if (device / 'wireless').is_dir():
            return device.name
    raise OSError('Primary Wi-Fi radio not ready')

class WifiWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title='Ubuntu — Connect to Wi-Fi')
        self.set_default_size(1050, 740)
        self.set_border_width(28)
        self.connect('destroy', Gtk.main_quit)
        self.shifted = False
        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        self.password.set_placeholder_text('Wi-Fi password')
        self.password.set_hexpand(True)
        self.ssid = Gtk.Entry()
        self.ssid.set_placeholder_text('Wi-Fi network name (SSID)')
        self.ssid.set_text(os.environ.get('T630_WIFI_SSID', ''))
        self.status = Gtk.Label(label='Enter the network name and password. The password stays on this tablet.')
        self.status.set_line_wrap(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.add(box)
        title = Gtk.Label()
        title.set_markup('<span size="24000" weight="bold">Connect Ubuntu to Wi-Fi</span>')
        box.pack_start(title, False, False, 0)
        box.pack_start(self.status, False, False, 0)
        box.pack_start(self.ssid, False, False, 0)
        box.pack_start(self.password, False, False, 0)
        show = Gtk.CheckButton(label='Show password')
        show.connect('toggled', lambda b: self.password.set_visibility(b.get_active()))
        box.pack_start(show, False, False, 0)
        self.keyboard = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.pack_start(self.keyboard, True, True, 0)
        self.draw_keys()
        self.connect_button = Gtk.Button(label='Connect')
        self.connect_button.set_size_request(-1, 60)
        self.connect_button.connect('clicked', self.connect_wifi)
        box.pack_start(self.connect_button, False, False, 0)
        css = Gtk.CssProvider()
        css.load_from_data(b'entry, button, label { font-size: 20px; } button { padding: 10px; }')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def insert(self, text):
        position = self.password.get_position()
        current = self.password.get_text()
        self.password.set_text(current[:position] + text + current[position:])
        self.password.set_position(position + len(text))

    def draw_keys(self):
        for child in self.keyboard.get_children():
            self.keyboard.remove(child)
        rows = ['1234567890-=', 'qwertyuiop[]', "asdfghjkl;'", 'zxcvbnm,./\\']
        shifted = ['!@#$%^&*()_+', 'QWERTYUIOP{}', 'ASDFGHJKL:"', 'ZXCVBNM<>?|']
        for letters in (shifted if self.shifted else rows):
            row = Gtk.Box(spacing=6, homogeneous=True)
            for character in letters:
                button = Gtk.Button(label=character)
                button.set_can_focus(False)
                button.connect('clicked', lambda _, c=character: self.insert(c))
                row.pack_start(button, True, True, 0)
            self.keyboard.pack_start(row, True, True, 0)
        row = Gtk.Box(spacing=8, homogeneous=True)
        for label, action in [('Shift', self.shift), ('Space', lambda: self.insert(' ')), ('Backspace', self.backspace), ('Clear', lambda: self.password.set_text(''))]:
            button = Gtk.Button(label=label)
            button.set_can_focus(False)
            button.connect('clicked', lambda _, fn=action: fn())
            row.pack_start(button, True, True, 0)
        self.keyboard.pack_start(row, True, True, 0)
        self.keyboard.show_all()

    def shift(self):
        self.shifted = not self.shifted
        self.draw_keys()

    def backspace(self):
        position = self.password.get_position()
        current = self.password.get_text()
        if position > 0:
            self.password.set_text(current[:position-1] + current[position:])
            self.password.set_position(position-1)

    def connect_wifi(self, _):
        secret = self.password.get_text()
        ssid = self.ssid.get_text().strip()
        if not ssid or not secret:
            self.status.set_text('Enter the network name and password first.')
            return
        self.connect_button.set_sensitive(False)
        self.status.set_text(f'Connecting to {ssid}…')
        def worker():
            try:
                # Secret goes through stdin, never shell interpolation, argv or logs.
                interface = primary_wifi()
                result = subprocess.run(['/usr/bin/nmcli', '--ask', '--wait', '40',
                                         'device', 'wifi', 'connect', ssid,
                                         'ifname', interface], input=secret+'\n', text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=50)
                success = result.returncode == 0
                if success:
                    profile = subprocess.run(
                        ['/usr/bin/nmcli', '-g', 'GENERAL.CONNECTION', 'device',
                         'show', interface], capture_output=True, text=True,
                        timeout=5, check=True).stdout.strip()
                    subprocess.run(['/usr/bin/nmcli', 'connection', 'modify', profile,
                                    'connection.interface-name', ''], capture_output=True,
                                   timeout=5, check=True)
            except (OSError, subprocess.SubprocessError):
                success = False
            GLib.idle_add(self.finished, success)
        threading.Thread(target=worker, daemon=True).start()

    def finished(self, success):
        self.connect_button.set_sensitive(True)
        if success:
            self.password.set_text('')
            self.status.set_text('Connected. You can close this window.')
        else:
            self.status.set_text('Connection did not complete. Check the password and try again.')
        return False

window = WifiWindow()
window.show_all()
Gtk.main()
