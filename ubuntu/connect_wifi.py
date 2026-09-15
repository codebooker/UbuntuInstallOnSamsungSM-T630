#!/usr/bin/python3
"""Local touch-friendly password entry. Never log or pass the secret in argv."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk
import subprocess
import threading
from pathlib import Path
import os
import fcntl

instance_lock = open('/run/t630-connect-wifi.lock', 'a')
try:
    fcntl.flock(instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)

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
        self.password = Gtk.Entry()
        self.password.set_visibility(False)
        self.password.set_placeholder_text('Wi-Fi password')
        self.password.set_hexpand(True)
        self.ssid = Gtk.ComboBoxText.new_with_entry()
        self.ssid.set_hexpand(True)
        self.ssid.get_child().set_placeholder_text('Wi-Fi network name (SSID)')
        self.status = Gtk.Label(label='Choose a network and enter its password. The password stays on this tablet.')
        self.status.set_line_wrap(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.add(box)
        title = Gtk.Label()
        title.set_markup('<span size="24000" weight="bold">Connect Ubuntu to Wi-Fi</span>')
        box.pack_start(title, False, False, 0)
        box.pack_start(self.status, False, False, 0)
        box.pack_start(self.ssid, False, False, 0)
        refresh = Gtk.Button(label='Refresh networks')
        refresh.connect('clicked', self.refresh_networks)
        box.pack_start(refresh, False, False, 0)
        box.pack_start(self.password, False, False, 0)
        show = Gtk.CheckButton(label='Show password')
        show.connect('toggled', lambda b: self.password.set_visibility(b.get_active()))
        box.pack_start(show, False, False, 0)
        self.connect_button = Gtk.Button(label='Connect')
        self.connect_button.set_size_request(-1, 60)
        self.connect_button.connect('clicked', self.connect_wifi)
        box.pack_start(self.connect_button, False, False, 0)
        css = Gtk.CssProvider()
        css.load_from_data(b'entry, button, label { font-size: 20px; } button { padding: 10px; }')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.refresh_networks()

    def visible_networks(self):
        try:
            result = subprocess.run(
                ['/usr/bin/nmcli', '-t', '-f', 'SSID,SIGNAL', 'device',
                 'wifi', 'list', '--rescan', 'yes'], capture_output=True,
                text=True, timeout=10, check=True)
        except (OSError, subprocess.SubprocessError):
            return []
        networks = {}
        for line in result.stdout.splitlines():
            try:
                name, strength = line.rsplit(':', 1)
                name = name.replace(r'\:', ':').replace(r'\\', '\\').strip()
                if name:
                    networks[name] = max(networks.get(name, 0), int(strength))
            except ValueError:
                continue
        return [name for name, _ in sorted(networks.items(),
                                           key=lambda item: (-item[1], item[0].lower()))]

    def refresh_networks(self, _button=None):
        current = self.ssid.get_child().get_text().strip()
        self.ssid.remove_all()
        networks = self.visible_networks()
        for name in networks:
            self.ssid.append_text(name)
        preferred = current or os.environ.get('T630_WIFI_SSID', '')
        if preferred:
            self.ssid.get_child().set_text(preferred)
        elif networks:
            self.ssid.set_active(0)
        self.status.set_text(
            'Choose a network and enter its password. The password stays on this tablet.'
            if networks else 'No networks found yet. You can type a hidden network name or refresh.')

    def connect_wifi(self, _):
        secret = self.password.get_text()
        ssid = self.ssid.get_child().get_text().strip()
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
window.password.grab_focus()
Gtk.main()
