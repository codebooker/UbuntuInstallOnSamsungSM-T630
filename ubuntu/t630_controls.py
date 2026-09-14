#!/usr/bin/python3
"""Small local tablet launcher and status panel. No network listeners or secrets."""
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner
OWNER = resolve_owner()

BATTERY = Path('/sys/class/power_supply/battery')
BACKLIGHT = Path('/sys/class/backlight/panel0-backlight')

def read_status():
    def read(name, fallback='Unavailable'):
        try:
            return (BATTERY/name).read_text().strip()
        except OSError:
            return fallback
    disk = shutil.disk_usage(OWNER.home)
    return {'capacity': read('capacity', '?'), 'charging': read('status'),
            'free_gib': round(disk.free/1024**3, 1),
            'total_gib': round(disk.total/1024**3, 1)}

def brightness_percent():
    maximum = int((BACKLIGHT/'max_brightness').read_text())
    return round(int((BACKLIGHT/'brightness').read_text())*100/maximum)

def set_brightness(percent):
    # Never turn the display fully off; do not touch charging-control nodes.
    if not 10 <= percent <= 100:
        raise ValueError('Brightness must be between 10 and 100 percent')
    maximum = int((BACKLIGHT/'max_brightness').read_text())
    value = max(1, round(maximum*percent/100))
    (BACKLIGHT/'brightness').write_text(str(value))
    return value

class Controls(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='local.t630.Controls',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.network_busy = False

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self, title='Tablet controls')
        self.window.set_default_size(980, 720)
        self.window.set_border_width(28)
        self.window.connect('destroy', self.closed)
        css = Gtk.CssProvider()
        css.load_from_data(b'''
            #tablet-controls { background: #21182c; }
            #tablet-controls label { font-size: 19px; }
            #tablet-controls .heading { font-size: 32px; font-weight: bold; }
            #tablet-controls .muted { color: #c3b8ce; }
            #tablet-controls .battery { font-size: 34px; font-weight: bold; color: #c6ebc9; }
            #tablet-controls button { min-height: 60px; padding: 8px 16px; }
            #tablet-controls scale slider { min-width: 28px; min-height: 28px; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window.set_name('tablet-controls')
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.window.add(outer)
        self.label(outer, 'Your Ubuntu tablet', 'heading')
        self.label(outer, 'Galaxy Tab Active4 Pro  ·  Native Ubuntu 24.04', 'muted')
        grid = Gtk.Grid(column_spacing=18, row_spacing=18, column_homogeneous=True)
        outer.pack_start(grid, False, False, 0)
        for index, (label, app, icon) in enumerate([
            ('Files', 'files', 'folder'), ('Text editor', 'editor', 'accessories-text-editor'),
            ('Terminal', 'terminal', 'utilities-terminal'),
            ('Connect Wi-Fi', 'wifi', 'network-wireless'),
            ('GNOME desktop', 'gnome', 'preferences-desktop')]):
            button = Gtk.Button(label=label)
            button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG))
            button.set_always_show_image(True)
            button.connect('clicked', lambda _, name=app: self.launch(name))
            grid.attach(button, index%2, index//2, 1, 1)
        self.battery = self.label(outer, '', 'battery')
        self.connection = self.label(outer, 'Checking Wi-Fi…', 'muted')
        row = Gtk.Box(spacing=18)
        outer.pack_start(row, False, False, 0)
        self.label(row, 'Brightness')
        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 1)
        self.slider.set_hexpand(True)
        self.slider.set_digits(0)
        self.slider.set_value(brightness_percent())
        self.slider.connect('value-changed', self.change_brightness)
        row.pack_start(self.slider, True, True, 0)
        self.storage = self.label(outer, '', 'muted')
        self.message = self.label(outer, 'Touch and S Pen ready. USB is optional for Wi-Fi administration.', 'muted')
        self.label(outer, f'Everyday apps use the {OWNER.username} account. SSH remains the administrator connection.', 'muted')
        password_button = Gtk.Button(label='Set local password / enable sudo')
        password_button.connect('clicked',lambda _:self.launch('password'))
        outer.pack_start(password_button,False,False,0)
        self.refresh()
        GLib.timeout_add_seconds(5, self.refresh)
        self.window.show_all()

    def label(self, box, text, style=None):
        label = Gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        if style:
            label.get_style_context().add_class(style)
        box.pack_start(label, False, False, 0)
        return label

    def launch(self, name):
        try:
            with open('/run/t630-desktop-apps.log', 'a') as log:
                subprocess.Popen(['/usr/local/bin/t630-app', name],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
        except OSError:
            self.message.set_text('Could not start the application. SSH remains available.')

    def change_brightness(self, slider):
        try:
            set_brightness(slider.get_value())
            self.message.set_text('Brightness adjusted for this session.')
        except (OSError, ValueError):
            self.message.set_text('Brightness could not be changed; current display stays on.')

    def refresh(self):
        if self.window is None:
            return False
        state = read_status()
        self.battery.set_text(f"{state['capacity']}%  ·  {state['charging']}")
        self.storage.set_text(f"Storage: {state['free_gib']} GiB free of {state['total_gib']} GiB")
        if not self.network_busy:
            self.network_busy = True
            threading.Thread(target=self.read_network, daemon=True).start()
        return True

    def read_network(self):
        try:
            devices = [device.name for device in Path('/sys/class/net').iterdir()
                       if (device / 'wireless').is_dir()]
            if len(devices) != 1:
                raise OSError('Primary Wi-Fi radio not ready')
            result = subprocess.run(['/usr/bin/nmcli', '-g', 'GENERAL.CONNECTION,IP4.ADDRESS',
                                     'device', 'show', devices[0]], capture_output=True,
                                    text=True, timeout=4, check=True)
            lines = [line for line in result.stdout.strip().splitlines() if line]
            text = 'Wi-Fi: ' + '  ·  '.join(lines) if lines else 'Wi-Fi: disconnected'
        except (OSError, subprocess.SubprocessError):
            text = 'Wi-Fi status unavailable'
        GLib.idle_add(self.network_done, text)

    def network_done(self, text):
        self.network_busy = False
        if self.window:
            self.connection.set_text(text)
        return False

    def closed(self, *_):
        self.window = None

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        state = read_status()
        assert 0 <= int(state['capacity']) <= 100
        assert state['free_gib'] > 0
        assert 0 <= brightness_percent() <= 100
        for invalid in (0, 101):
            try:
                set_brightness(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError('Unsafe brightness accepted')
        print(json.dumps(state))
    else:
        ctypes.CDLL(None).prctl(15, b't630-controls', 0, 0, 0)
        raise SystemExit(Controls().run(sys.argv))
