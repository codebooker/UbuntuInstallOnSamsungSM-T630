# Utilities folder and drawing-app discovery — 2026-09-15

The owner reported that X-GNOME Utilities still would not open and the drawing
app was not discoverable. Inspection of the live app grid showed MyPaint on its
third row, but with an easily missed icon. Its native desktop entry existed,
resolved through Gio, and reported `should_show: true`. Xournal++ remained open
with the owner's note; no restart, note closure, or preference reset was needed.

## Persistent folder fix

The prior fix set `folder-children` empty after Shell acquired its bus name.
This is not a reliable initialization boundary: GNOME's AppDisplay
[`_ensureDefaultFolders`](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/appDisplay.js#L1328)
recreates Utilities/YaST/Pardus when it sees an empty list. The live setting had
returned to those three default IDs, confirming the previous fix was incomplete.

The packaged `t630-app-grid` now runs **before** Shell starts. It removes only
those stock default folder IDs and retains personal folder IDs, adding one
reserved empty `t630-flat-layout` entry. Shell omits empty folders from the grid,
but the nonempty settings list prevents it from recreating the stock defaults.
No Shell patch, unsafe-mode switch, periodic settings enforcement, or global
user-profile reset is used.

The helper also initializes default favorites only when no user value exists.
Previously the session reset favorites on every start, which would have removed
the drawing shortcut on reboot. Existing favorites, including an intentionally
empty list, are now retained. `--pin-drawing` appends only `mypaint.desktop` when
the app is installed and does not duplicate or replace the owner's pins.

## Drawing app and live verification

- Renamed the desktop entry to **MyPaint Drawing**; it still launches through
  the normal-owner native-Wayland pen-app helper with the original file arguments.
- Updated the optional pen-app install recipe to pin it in a running owner
  GNOME session, without requiring that session for package installation.
- Applied the packaged layout helper through the owner's existing GNOME bus.
  The resulting folder list is `['t630-flat-layout']` and the favorite list
  contains `mypaint.desktop`.
- The physical live-view screenshot showed the dead folder removed, individual
  utility icons present, and MyPaint pinned to the bottom dock.
- Launching the installed MyPaint desktop entry returned success, created the
  normal-owner process, and showed its canvas window thumbnail in the overview.
  Owner confirmation of tapping the dock icon is requested separately; pressure
  and wider drawing acceptance remain unchanged.
- A normal Shell `FocusApp` diagnostic was rejected by its access policy. That
  policy was not disabled, and no lock/authentication boundary was bypassed.

## Updated exact release closure

| Package | SHA256 |
| --- | --- |
| t630-desktop-runtime 0.1.3 all | a994884cb84305c01023d1e6ef6cbd0542eff34f9c9ba2cd65098311413a819e |
| t630-hardware-runtime 0.1.4 all | 9f0bfe0e67a13e1d8d47e73830f26c6ca946bba61276695a2eb85d9952dda4ed |
| t630-release-base 0.1.11 arm64 | faa09b361ce86783ccebd88640b2e419a4ca519def05c1b2191c2c3d57ff4514 |

These three packages installed/configured on the personalized clean root with
empty `dpkg --audit`. The offline assembler pins the updated closure. Builds
were repeated byte-for-byte, and the assembler validated all 14 staged packages
on-device through a temporary read-only bind mount that was then removed.
The full suite completed with 247 passes and four environment-dependent skips.
Tests cover stock-default flattening, empty-sentinel
state, preservation of personal folders and favorites, idempotent drawing pins,
intentionally empty favorites, native desktop naming, and pre-Shell ordering.
Restart persistence of this new fix is not yet physically tested; the code is
packaged and the live grid change is verified.
