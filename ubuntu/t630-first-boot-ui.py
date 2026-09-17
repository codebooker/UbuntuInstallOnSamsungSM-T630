#!/usr/bin/python3
"""Touch-first setup wizard for a fresh SM-T630 Ubuntu installation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

# Direct recovery-compositor previews need the local text-input-v1 bridge.
# The normal setup host is GNOME and deliberately keeps GTK's native input
# method so GNOME Shell can provide the same keyboard as the finished desktop.
if os.environ.get("T630_FIRST_BOOT_GNOME") != "1":
    os.environ.setdefault("GTK_IM_MODULE", "t630-wayland")
    os.environ.setdefault(
        "GTK_IM_MODULE_FILE", "/usr/local/share/t630/gtk-immodules.cache"
    )

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

sys.path.insert(0, "/usr/local/share/t630")
from t630_first_boot import SetupError, SetupProfile, validate_profile, validate_password


LANGUAGES = (
    ("English (United States)", "en_US.UTF-8"),
    ("English (United Kingdom)", "en_GB.UTF-8"),
    ("Deutsch", "de_DE.UTF-8"),
    ("Español", "es_ES.UTF-8"),
    ("Français", "fr_FR.UTF-8"),
)
KEYBOARDS = (("English (US)", "us"), ("English (UK)", "gb"), ("German", "de"),
             ("Spanish", "es"), ("French", "fr"))
TIMEZONES = ("America/New_York", "America/Chicago", "America/Denver",
             "America/Los_Angeles", "Europe/London", "Europe/Paris",
             "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney")


class FirstBoot(Gtk.Window):
    def __init__(self, preview=False):
        if os.geteuid() != 0 or (Path("/etc/t630/owner").exists() and not preview):
            raise SystemExit("First-boot setup is not required")
        self.preview = preview
        super().__init__(title="Ubuntu setup preview" if preview else "Welcome to Ubuntu")
        self.set_default_size(1200, 800)
        self.fullscreen()
        self.connect("destroy", Gtk.main_quit)
        self.pages = []
        self.index = 0
        self.busy = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        outer.set_border_width(36)
        self.add(outer)
        if self.preview:
            banner = Gtk.Label(
                label="Preview mode — closing this window will discard every entry and make no system changes.",
                xalign=0,
            )
            banner.set_line_wrap(True)
            outer.pack_start(banner, False, False, 0)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
                               transition_duration=220)
        outer.pack_start(self.stack, True, True, 0)
        nav = Gtk.Box(spacing=14)
        outer.pack_end(nav, False, False, 0)
        self.status = Gtk.Label(xalign=0)
        self.status.set_line_wrap(True)
        nav.pack_start(self.status, True, True, 0)
        self.back = Gtk.Button(label="Back")
        self.back.connect("clicked", self.go_back)
        self.next = Gtk.Button(label="Next")
        self.next.get_style_context().add_class("suggested-action")
        self.next.connect("clicked", self.go_next)
        nav.pack_end(self.next, False, False, 0)
        nav.pack_end(self.back, False, False, 0)

        self.build_pages()
        css = Gtk.CssProvider()
        css.load_from_data(b"label.title { font-size: 34px; font-weight: bold; } entry, button, combobox, label { font-size: 20px; } entry, button { min-height: 54px; }")
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.show_page(0)

    def page(self, title, description):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        heading = Gtk.Label(label=title, xalign=0)
        heading.get_style_context().add_class("title")
        box.pack_start(heading, False, False, 0)
        subtitle = Gtk.Label(label=description, xalign=0)
        subtitle.set_line_wrap(True)
        box.pack_start(subtitle, False, False, 0)
        name = f"page-{len(self.pages)}"
        self.stack.add_named(box, name)
        self.pages.append((name, box))
        return box

    @staticmethod
    def combo(options):
        widget = Gtk.ComboBoxText()
        for label, value in options:
            widget.append(value, label)
        widget.set_active(0)
        return widget

    @staticmethod
    def switch_row(page, label):
        row = Gtk.Box(spacing=18)
        row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
        toggle = Gtk.Switch()
        row.pack_end(toggle, False, False, 0)
        page.pack_start(row, False, False, 0)
        return toggle

    def build_pages(self):
        page = self.page("Welcome to Ubuntu", "Choose the language used by the desktop.")
        self.language = self.combo(LANGUAGES)
        page.pack_start(self.language, False, False, 0)

        page = self.page("Accessibility", "These choices can be changed later in Settings.")
        self.large_text = self.switch_row(page, "Large text")
        self.high_contrast = self.switch_row(page, "High contrast")
        self.screen_reader = self.switch_row(page, "Screen reader")

        page = self.page("Keyboard", "Choose the layout for physical and on-screen typing.")
        self.keyboard = self.combo(KEYBOARDS)
        page.pack_start(self.keyboard, False, False, 0)

        page = self.page("Connect to a network", "Internet access enables updates and the app store. You can also continue offline.")
        self.network = Gtk.Label(label="Checking Wi-Fi…", xalign=0)
        page.pack_start(self.network, False, False, 0)
        self.wifi_ssid = Gtk.ComboBoxText.new_with_entry()
        self.wifi_ssid.set_hexpand(True)
        self.wifi_ssid.get_child().set_placeholder_text("Wi-Fi network name (SSID)")
        page.pack_start(self.wifi_ssid, False, False, 0)
        self.wifi_password = Gtk.Entry(placeholder_text="Wi-Fi password")
        self.wifi_password.set_visibility(False)
        page.pack_start(self.wifi_password, False, False, 0)
        wifi_actions = Gtk.Box(spacing=14)
        refresh = Gtk.Button(label="Refresh networks")
        refresh.connect("clicked", self.refresh_wifi_networks)
        refresh.set_sensitive(not self.preview)
        wifi_actions.pack_start(refresh, True, True, 0)
        self.wifi_connect = Gtk.Button(label="Connect")
        self.wifi_connect.connect("clicked", self.connect_wifi)
        self.wifi_connect.set_sensitive(not self.preview)
        wifi_actions.pack_start(self.wifi_connect, True, True, 0)
        page.pack_start(wifi_actions, False, False, 0)
        GLib.timeout_add_seconds(2, self.refresh_network)

        page = self.page("Create your account", "This account owns your files, applications, and device settings.")
        self.full_name = Gtk.Entry(placeholder_text="Your name")
        self.username = Gtk.Entry(placeholder_text="Username")
        self.hostname = Gtk.Entry(placeholder_text="Computer name")
        self.hostname.set_text("ubuntu-tab")
        self.password = Gtk.Entry(placeholder_text="Password (at least 8 characters)")
        self.password.set_visibility(False)
        self.confirm = Gtk.Entry(placeholder_text="Confirm password")
        self.confirm.set_visibility(False)
        for widget in (self.full_name, self.username, self.hostname, self.password, self.confirm):
            page.pack_start(widget, False, False, 0)

        page = self.page("Time zone", "Choose the time zone used for the clock and calendar.")
        self.timezone = self.combo(tuple((zone.replace("_", " "), zone) for zone in TIMEZONES))
        page.pack_start(self.timezone, False, False, 0)

        page = self.page("Privacy", "Location services are off by default and can be changed later.")
        self.location = self.switch_row(page, "Enable location services")

        page = self.page("Ready to use Ubuntu", "Review your choices, then create the account. Your password stays on this tablet.")
        self.review = Gtk.Label(xalign=0)
        self.review.set_line_wrap(True)
        page.pack_start(self.review, False, False, 0)

    def selected_profile(self):
        return SetupProfile(
            username=self.username.get_text().strip(),
            full_name=self.full_name.get_text().strip(),
            hostname=self.hostname.get_text().strip(),
            timezone=self.timezone.get_active_id(),
            locale=self.language.get_active_id(),
            keyboard_layout=self.keyboard.get_active_id(),
            location_services=self.location.get_active(),
            large_text=self.large_text.get_active(),
            high_contrast=self.high_contrast.get_active(),
            screen_reader=self.screen_reader.get_active(),
        )

    def show_page(self, index):
        self.index = index
        self.stack.set_visible_child_name(self.pages[index][0])
        self.back.set_sensitive(index > 0 and not self.busy)
        if index == len(self.pages) - 1:
            self.next.set_label("Close preview" if self.preview else "Create account")
        else:
            self.next.set_label("Next")
        self.next.set_sensitive(not self.busy)
        self.status.set_text("")
        if index == 4:
            GLib.idle_add(self.focus_account_entry)
        if index == 3 and not self.preview:
            GLib.idle_add(self.refresh_wifi_networks)
        if index == len(self.pages) - 1:
            try:
                profile = self.selected_profile()
                validate_profile(profile)
                validate_password(self.password.get_text())
                if self.password.get_text() != self.confirm.get_text():
                    raise SetupError("the passwords do not match")
                self.review.set_text(
                    f"Name: {profile.full_name}\nUsername: {profile.username}\n"
                    f"Computer: {profile.hostname}\nTime zone: {profile.timezone}\n"
                    f"Language: {profile.locale}\nKeyboard: {profile.keyboard_layout}")
            except SetupError as exc:
                self.review.set_text(f"Go Back and correct: {exc}")

    def focus_account_entry(self):
        self.full_name.grab_focus()
        return False

    def go_back(self, _button):
        if not self.busy and self.index > 0:
            self.show_page(self.index - 1)

    def go_next(self, _button):
        if self.busy:
            return
        if self.index < len(self.pages) - 1:
            self.show_page(self.index + 1)
            return
        if self.preview:
            self.password.set_text("")
            self.confirm.set_text("")
            self.destroy()
            return
        try:
            profile = self.selected_profile()
            validate_profile(profile)
            secret = self.password.get_text()
            validate_password(secret)
            if secret != self.confirm.get_text():
                raise SetupError("the passwords do not match")
        except SetupError as exc:
            self.status.set_text(str(exc))
            return
        self.busy = True
        self.back.set_sensitive(False)
        self.next.set_sensitive(False)
        self.status.set_text("Creating your Ubuntu account…")
        threading.Thread(target=self.apply, args=(profile, secret), daemon=True).start()

    def apply(self, profile, secret):
        path = None
        try:
            descriptor, name = tempfile.mkstemp(prefix="t630-first-boot.", suffix=".json", dir="/run")
            path = Path(name)
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(profile.__dict__, stream)
                stream.flush()
                os.fsync(stream.fileno())
            result = subprocess.run(
                ["/usr/bin/python3", "/usr/local/share/t630/t630_first_boot.py", "--profile", str(path)],
                input=secret + "\n", text=True, capture_output=True, timeout=120)
            success = result.returncode == 0
            message = "Setup complete. Starting Ubuntu…" if success else "Setup could not finish. Check the fields and try again."
        except (OSError, subprocess.SubprocessError):
            success = False
            message = "Setup could not finish. Check the fields and try again."
        finally:
            secret = ""
            if path is not None:
                path.unlink(missing_ok=True)
        GLib.idle_add(self.finished, success, message)

    def finished(self, success, message):
        self.password.set_text("")
        self.confirm.set_text("")
        self.status.set_text(message)
        if success:
            GLib.timeout_add_seconds(2, self.close_success)
        else:
            self.busy = False
            self.back.set_sensitive(True)
            self.next.set_sensitive(True)
        return False

    def close_success(self):
        self.destroy()
        return False

    @staticmethod
    def primary_wifi():
        # qcacld exposes client, soft-AP and P2P interfaces.  Directory order
        # is nondeterministic, and selecting swlan0/p2p0 makes the stock
        # regulatory worker dereference an invalid vdev on its first scan.
        client = Path("/sys/class/net/wlan0")
        if (client / "wireless").is_dir():
            return client.name
        for device in sorted(Path("/sys/class/net").iterdir()):
            if ((device / "wireless").is_dir()
                    and not device.name.startswith(("swlan", "p2p"))):
                return device.name
        raise OSError("Primary Wi-Fi radio not ready")

    @staticmethod
    def visible_networks():
        try:
            result = subprocess.run(
                ["/usr/bin/nmcli", "-t", "-f", "SSID,SIGNAL", "device",
                 "wifi", "list", "--rescan", "yes"], capture_output=True,
                text=True, timeout=10, check=True)
        except (OSError, subprocess.SubprocessError):
            return []
        networks = {}
        for line in result.stdout.splitlines():
            try:
                name, strength = line.rsplit(":", 1)
                name = name.replace(r"\:", ":").replace(r"\\", "\\").strip()
                if name:
                    networks[name] = max(networks.get(name, 0), int(strength))
            except ValueError:
                continue
        return [name for name, _ in sorted(
            networks.items(), key=lambda item: (-item[1], item[0].lower()))]

    def refresh_wifi_networks(self, _button=None):
        self.status.set_text("Scanning for Wi-Fi networks…")
        threading.Thread(target=self.scan_wifi_worker, daemon=True).start()
        return False

    def scan_wifi_worker(self):
        GLib.idle_add(self.finish_wifi_scan, self.visible_networks())

    def finish_wifi_scan(self, networks):
        current = self.wifi_ssid.get_child().get_text().strip()
        self.wifi_ssid.remove_all()
        for name in networks:
            self.wifi_ssid.append_text(name)
        if current:
            self.wifi_ssid.get_child().set_text(current)
        elif networks:
            preferred = os.environ.get("T630_WIFI_SSID", "")
            self.wifi_ssid.set_active(
                networks.index(preferred) if preferred in networks else 0)
        self.status.set_text(
            "Choose a network and enter its password."
            if networks else "No networks found yet. Type a hidden network name or refresh.")
        self.wifi_password.grab_focus()
        return False

    def connect_wifi(self, _button):
        ssid = self.wifi_ssid.get_child().get_text().strip()
        secret = self.wifi_password.get_text()
        if not ssid or not secret:
            self.status.set_text("Choose a network and enter its password first.")
            self.wifi_password.grab_focus()
            return
        self.wifi_connect.set_sensitive(False)
        self.status.set_text(f"Connecting to {ssid}…")
        threading.Thread(target=self.connect_wifi_worker,
                         args=(ssid, secret), daemon=True).start()

    def connect_wifi_worker(self, ssid, secret):
        try:
            interface = self.primary_wifi()
            result = subprocess.run(
                ["/usr/bin/nmcli", "--ask", "--wait", "40", "device",
                 "wifi", "connect", ssid, "ifname", interface],
                input=secret + "\n", text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=50)
            success = result.returncode == 0
            if success:
                # Association and DHCP are the user-visible success boundary.
                # Persistence tuning is best-effort: rejecting an already-live
                # connection here makes the wizard falsely blame the password.
                try:
                    profile = subprocess.run(
                        ["/usr/bin/nmcli", "-g", "GENERAL.CONNECTION", "device",
                         "show", interface], capture_output=True, text=True,
                        timeout=5, check=True).stdout.strip()
                    hardware_address = Path(
                        f"/sys/class/net/{interface}/address").read_text().strip()
                    if not hardware_address:
                        raise OSError("Primary Wi-Fi MAC address is unavailable")
                    subprocess.run(
                        ["/usr/bin/nmcli", "connection", "modify", profile,
                         "connection.interface-name", "",
                         "802-11-wireless.mac-address", hardware_address],
                        capture_output=True, timeout=5, check=True)
                except (OSError, subprocess.SubprocessError):
                    pass
        except (OSError, subprocess.SubprocessError):
            success = False
        finally:
            secret = ""
        GLib.idle_add(self.finish_wifi_connection, success)

    def finish_wifi_connection(self, success):
        self.wifi_connect.set_sensitive(True)
        self.wifi_password.set_text("")
        self.status.set_text(
            "Connected. You can continue setup."
            if success else "Connection did not complete. Check the password and try again.")
        return False

    def refresh_network(self):
        try:
            result = subprocess.run(
                ["/usr/bin/nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=3, check=True)
            names = [name for name in result.stdout.splitlines() if name and name != "lo"]
            self.network.set_text("Connected" if names else "Not connected")
        except (OSError, subprocess.SubprocessError):
            self.network.set_text("Wi-Fi status unavailable")
        return True


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--preview"]):
        raise SystemExit("usage: t630-first-boot [--preview]")
    window = FirstBoot(preview=sys.argv[1:] == ["--preview"])
    window.show_all()
    Gtk.main()
