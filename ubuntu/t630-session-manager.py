#!/usr/bin/python3
"""Expose the active custom tablet session to GNOME settings daemons."""
import os
from pathlib import Path
import re
import signal
import sys

from gi.repository import Gio, GLib

sys.path.insert(0, '/usr/local/share/t630')
from t630_account import resolve_owner


MANAGER_XML = """<node><interface name='org.gnome.SessionManager'>
<method name='RegisterClient'><arg type='s' direction='in'/><arg type='s' direction='in'/><arg type='o' direction='out'/></method>
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


def client_method(_bus, _sender, _path, _iface, method, _params, invocation):
    if method == 'EndSessionResponse':
        invocation.return_value(None)


def manager_method(_bus, _sender, _path, _iface, method, _params, invocation):
    if method != 'RegisterClient':
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
