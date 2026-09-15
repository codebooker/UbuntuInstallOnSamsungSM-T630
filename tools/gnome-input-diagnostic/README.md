# Manual GNOME 46 input diagnostic

This is a lab instrument, not a touchscreen repair, release package, or
startup/watchdog component. It observes the existing tablet GNOME session.
It never changes grabs, opens UI, injects or consumes input, or alters
authentication. Only touch/button event-type totals and overview/modal state
are logged. No keystrokes, text, coordinates, application titles, or password
events are recorded. The extension supports only the unlocked user session.

For a deliberate diagnostic run, copy these two source files into the selected
owner's `XDG_DATA_HOME/gnome-shell/extensions/t630-input-diagnostic@local/`.
Preserve the owner's enabled-extension list when adding this UUID, then start
a fresh managed GNOME session through the normal guarded launcher. GNOME 46
does not support the deprecated DBus `ReloadExtension` method; do not enable
unsafe-mode or use arbitrary Shell evaluation to work around that restriction.

Each unlocked activation observes at most 60 three-second samples, then
disconnects its event observer. Locking/disabling disconnects both the observer
and timer. After the test, run this as the selected owner:

```sh
/usr/local/bin/t630-gnome-run /usr/bin/gnome-extensions disable t630-input-diagnostic@local
```

The source files may remain installed but disabled for a future explicit test.
The standard owner-assets installer does not install or enable this diagnostic.
Confirm ordinary input still works after disabling it; a successful instrumented
session alone does not establish a durable fix.
