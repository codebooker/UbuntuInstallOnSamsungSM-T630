#!/usr/bin/python3
"""Show GNOME's OSK when Chrome focuses an editable accessible object."""

from __future__ import annotations

import signal

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi, Gio, GLib


SHELL_NAME = "org.gnome.Shell"
OBJECT_PATH = "/org/gnome/Shell/Extensions/T630TabletTools"
INTERFACE = "org.gnome.Shell.Extensions.T630TabletTools"
CHROME_APPLICATIONS = frozenset(("Google Chrome", "Chromium"))


class ChromeKeyboard:
    def __init__(self) -> None:
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.requested_visible = False
        self.poll_timer = 0
        self.listener = Atspi.EventListener.new(self._focus_changed, None)

    @staticmethod
    def _is_chrome(source: Atspi.Accessible) -> bool:
        try:
            application = source.get_application()
            return application is not None and application.get_name() in CHROME_APPLICATIONS
        except GLib.Error:
            return False

    @staticmethod
    def _is_editable(source: Atspi.Accessible) -> bool:
        try:
            return source.get_state_set().contains(Atspi.StateType.EDITABLE)
        except GLib.Error:
            return False

    def _call_shell(self, method: str) -> None:
        def finished(connection: Gio.DBusConnection, result: Gio.AsyncResult) -> None:
            try:
                connection.call_finish(result)
            except GLib.Error:
                # Shell may be restarting; a later focus event will retry.
                pass

        self.bus.call(
            SHELL_NAME,
            OBJECT_PATH,
            INTERFACE,
            method,
            None,
            None,
            Gio.DBusCallFlags.NONE,
            2000,
            None,
            finished,
        )

    def _show(self) -> None:
        if not self.requested_visible:
            self.requested_visible = True
            self._call_shell("ShowKeyboard")

    def _focused_chrome_editable(self) -> bool:
        desktop = Atspi.get_desktop(0)
        for index in range(desktop.get_child_count()):
            try:
                application = desktop.get_child_at_index(index)
                if application is None or application.get_name() not in CHROME_APPLICATIONS:
                    continue
                matches = Atspi.Collection.get_matches(
                    application,
                    self.focus_rule,
                    Atspi.CollectionSortOrder.CANONICAL,
                    1,
                    True,
                )
                if matches:
                    return True
            except (AttributeError, GLib.Error):
                continue
        return False

    def _poll_focus(self) -> bool:
        if self._focused_chrome_editable():
            self._show()
        else:
            # Let Chrome's normal text-input-v3 disable request close the OSK.
            # Sending our own HideKeyboard while focus moves to a native app
            # can race and close that app's correctly requested keyboard.
            self.requested_visible = False
        return GLib.SOURCE_CONTINUE

    def _focus_changed(self, event: Atspi.Event, _user_data: object = None) -> None:
        source = event.source
        if source is None or not self._is_chrome(source) or not self._is_editable(source):
            return
        if event.detail1:
            # Chrome can leave editable objects in background tabs marked as
            # focused. A real focus-gained event is nevertheless authoritative
            # for the newly selected tab, so never deduplicate this call.
            self.requested_visible = True
            self._call_shell("ShowKeyboard")
        else:
            self.requested_visible = False

    def run(self) -> None:
        Atspi.init()
        states = Atspi.StateSet.new(
            [Atspi.StateType.FOCUSED, Atspi.StateType.EDITABLE]
        )
        self.focus_rule = Atspi.MatchRule.new(
            states,
            Atspi.CollectionMatchType.ALL,
            {},
            Atspi.CollectionMatchType.ALL,
            [],
            Atspi.CollectionMatchType.ALL,
            [],
            Atspi.CollectionMatchType.ALL,
            False,
        )
        self.listener.register("object:state-changed:focused")
        self.poll_timer = GLib.timeout_add(400, self._poll_focus)
        def quit_loop() -> bool:
            Atspi.event_quit()
            return GLib.SOURCE_REMOVE

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_loop)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_loop)
        try:
            Atspi.event_main()
        finally:
            if self.poll_timer:
                GLib.source_remove(self.poll_timer)
            self.listener.deregister("object:state-changed:focused")


if __name__ == "__main__":
    ChromeKeyboard().run()
