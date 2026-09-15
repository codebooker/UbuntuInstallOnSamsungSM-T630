#!/usr/bin/python3
"""Expose the active custom tablet session to GNOME settings daemons."""
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner


MANAGER_XML = """<node><interface name='org.gnome.SessionManager'>
<method name='RegisterClient'><arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='o' direction='out'/></method>
<method name='Logout'><arg type='u' direction='in'/></method>
<method name='Shutdown'/><method name='Reboot'/>
<method name='CanShutdown'><arg type='b' direction='out'/></method>
<method name='IsInhibited'><arg type='u' direction='in'/><arg type='b' direction='out'/></method>
<property name='SessionName' type='s' access='read'/>
<property name='SessionIsActive' type='b' access='read'/>
<property name='InhibitedActions' type='u' access='read'/>
</interface></node>"""

CLIENT_XML = """<node><interface name='org.gnome.SessionManager.ClientPrivate'>
<method name='EndSessionResponse'><arg type='b' direction='in'/><arg type='s' direction='in'/></method>
<signal name='QueryEndSession'><arg type='u'/></signal>
<signal name='EndSession'><arg type='u'/></signal>
<signal name='Stop'/>
</interface></node>"""

session_id = os.environ.get('XDG_SESSION_ID', '')
# systemd-logind normally returns cNN; this tablet's elogind can return a
# numeric NN form after session recreation. Both originate from CreateSession
# in the root-only wrapper and are valid local session identifiers.
owner = resolve_owner()
if os.geteuid() != owner.uid or not re.fullmatch(r'c?[0-9]+', session_id):
    raise SystemExit('Only for the registered tablet login session.')
if Path('/etc/t630-install-id').read_text().strip() != 'SM-T630-T630XXSBDZE3-Ubuntu-v1':
    raise SystemExit('Wrong device installation.')

manager_info = Gio.DBusNodeInfo.new_for_xml(MANAGER_XML).interfaces[0]
client_info = Gio.DBusNodeInfo.new_for_xml(CLIENT_XML).interfaces[0]
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
clients = []
pending_action = None

DIALOG_BUS = 'org.gnome.Shell'
DIALOG_PATH = '/org/gnome/SessionManager/EndSessionDialog'
DIALOG_INTERFACE = 'org.gnome.SessionManager.EndSessionDialog'


def open_end_session_dialog(action):
    dialog_type = {'logout': 0, 'poweroff': 1, 'reboot': 2}[action]
    bus.call(DIALOG_BUS, DIALOG_PATH, DIALOG_INTERFACE, 'Open',
             GLib.Variant('(uuuao)', (dialog_type, 0, 60, [])), None,
             Gio.DBusCallFlags.NONE, 5000, None, end_session_dialog_opened,
             action)
    return GLib.SOURCE_REMOVE


def end_session_dialog_opened(connection, result, action):
    global pending_action
    try:
        connection.call_finish(result)
    except GLib.Error as exc:
        pending_action = None
        print(f'Could not open {action} confirmation: {exc.message}', flush=True)


def confirmed_dialog(_bus, _sender, _path, _interface, signal_name, _parameters):
    global pending_action
    if signal_name in ('Canceled', 'Closed'):
        pending_action = None
        return
    expected = {'ConfirmedLogout': 'logout', 'ConfirmedShutdown': 'poweroff',
                'ConfirmedReboot': 'reboot'}.get(signal_name)
    if expected is None or pending_action != expected:
        return
    pending_action = None
    if expected == 'logout':
        # This single-user nested session cannot safely expose the recovery
        # compositor as a logged-out desktop. Treat confirmed logout as lock.
        bus.call_sync(DIALOG_BUS, '/org/gnome/ScreenSaver', 'org.gnome.ScreenSaver',
                      'Lock', None, None, Gio.DBusCallFlags.NONE, 5000, None)
        return
    try:
        subprocess.run(['/usr/local/bin/t630-display', 'power',
                        'off' if expected == 'poweroff' else 'restart'],
                       check=True, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f'Confirmed {expected} request failed: {type(exc).__name__}', flush=True)


def client_method(_bus, _sender, _path, _iface, method, _params, invocation):
    if method == 'EndSessionResponse':
        invocation.return_value(None)


def manager_method(_bus, _sender, _path, _iface, method, _params, invocation):
    global pending_action
    if method == 'CanShutdown':
        invocation.return_value(GLib.Variant('(b)', (True,)))
        return
    if method == 'IsInhibited':
        invocation.return_value(GLib.Variant('(b)', (False,)))
        return
    if method in ('Logout', 'Shutdown', 'Reboot'):
        if pending_action is not None:
            invocation.return_dbus_error('org.gnome.SessionManager.Busy',
                                         'Another confirmation is already open.')
            return
        pending_action = {'Logout': 'logout', 'Shutdown': 'poweroff',
                          'Reboot': 'reboot'}[method]
        invocation.return_value(None)
        GLib.idle_add(open_end_session_dialog, pending_action)
        return
    if method != 'RegisterClient':
        invocation.return_dbus_error('org.gnome.SessionManager.Unsupported',
                                     'Unsupported session request.')
        return
    path = f'/org/gnome/SessionManager/Client{len(clients) + 1}'
    reg_id = bus.register_object(path, client_info, client_method, None, None)
    clients.append(reg_id)
    invocation.return_value(GLib.Variant('(o)', (path,)))


def manager_property(_bus, _sender, _path, _iface, prop):
    values = {
        'SessionName': GLib.Variant('s', 't630-lab-session'),
        'SessionIsActive': GLib.Variant('b', True),
        'InhibitedActions': GLib.Variant('u', 0),
    }
    return values[prop]


bus.register_object('/org/gnome/SessionManager', manager_info,
                    manager_method, manager_property, None)
bus.signal_subscribe(None, DIALOG_INTERFACE, None, DIALOG_PATH, None,
                     Gio.DBusSignalFlags.NONE, confirmed_dialog)
reply = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                      'org.freedesktop.DBus', 'RequestName',
                      GLib.Variant('(su)', ('org.gnome.SessionManager', 4)),
                      GLib.VariantType('(u)'), Gio.DBusCallFlags.NONE, 5000, None)
if reply.unpack()[0] != 1:
    raise SystemExit('GNOME SessionManager name is already owned.')

signal.signal(signal.SIGTERM, lambda *_: loop.quit())
signal.signal(signal.SIGINT, lambda *_: loop.quit())
print('GNOME session activity bridge ready.', flush=True)
loop.run()
