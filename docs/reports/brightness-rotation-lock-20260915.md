# Brightness persistence and physical rotation lock — 2026-09-15

The owner reported that the top-right brightness slider did not control the
screen, and Rotation Lock did not prevent rotation.

## Diagnosed paths

The normal-owner `t630-display brightness 55` request changed the exact known
panel brightness node from 255 to 168 (maximum 306), and status reported 55%.
After the delayed preferences flush, the Power/display monitor exited with
`FileNotFoundError` opening `/var/lib/t630/display-settings.new`: its parent
directory was absent on the clean root. The socket then refused connections.
This also endangered Power/lock/wake and other display-service controls, not just
brightness. The standard GNOME Power brightness property path did not produce
the requested hardware value during the separate bounded test; its precise
failure cause was not assigned. There were two brightness paths in Quick Settings.

The calibrated rotation controller never consulted a user rotation-lock setting.
The standard GNOME toggle instead controls
`org.gnome.settings-daemon.peripherals.touchscreen orientation-lock`, which the
session intentionally sets true to isolate Mutter's relative nested rotation
handler. Sensor-triggered absolute rotations could therefore continue despite
the visible standard control. See the upstream
[GNOME 46 rotation toggle](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/status/autoRotate.js)
and [Quick Settings indicator layout](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/panel.js).

## Repairs

- Desktop package post-install creates `/var/lib/t630` privately. Preferences
  flush also creates a missing state directory and refuses a symlinked parent.
  An I/O failure retains dirty preferences for rate-limited retry instead of
  terminating the Power/lock/wake monitor. Saved files remain root-only, accessed
  by the owner through the existing credential-checked local socket.
- Tablet Controls 7 suppresses the two mismatched standard Quick Settings items,
  including later visibility changes, and restores their visibility on disable.
  The existing hardware-backed brightness slider remains.
- A visible positive **Rotation Lock** toggle and the calibrated controller share
  the owner-local `rotation-locked` boolean. Lock cancels even queued rotations;
  unlock queues the current sensor reading with a fresh debounce interval.
  Mutter's relative handler remains isolated. No coordinate/sensor calibration
  or device permissions were changed.

The new owner setting was initialized true to honor the owner's explicit report
that Rotation Lock was on. Brightness was restored to the pre-test 83%. The
previous automatic-suspend choice remains false; it was not overridden.

## Packaging and live deployment

Reproducible epoch-zero packages, exact hashes reflected in the offline assembler:

| Package | SHA256 |
| --- | --- |
| `t630-desktop-runtime_0.1.4_all.deb` | `daddaa1a4a661b359a391aa119c2ca5a8278445d41972350b2f8622fc87482f8` |
| `t630-hardware-runtime_0.1.5_all.deb` | `01dc907cd4f3879032f70c6ccc702e731bba57cdb3d1d208642ee07d3ffbd8fd` |
| `t630-release-base_0.1.12_arm64.deb` | `d230d7c43c7c1cb50d5a3dca384971d029b946c3295bca81b2891d558e2e5362` |

Uploaded via the existing USB recovery console with transfer hashes verified,
staged with private file permissions, and installed normally on the selected
clean root. Exact package versions were queried. Restarted only the already
failed display monitor, and the normal-owner brightness/status request answered
again. Updated and compiled owner extension assets via the existing guarded
installer.

Before the orderly restart, copied MyPaint's autosave cache/settings into the
unique normal-owner directory
`Documents/MyPaint-before-controls-restart-qKkSFH` (1,152 KiB). Nothing was deleted
or uploaded from that backup. The restart was requested through the repaired
guarded display-service path; no new boot image/kernel/partition change occurred.

All 261 tests completed (257 passes, four skips); new tests cover missing private
state directories, persistence failure/retry without lost controls, symlink
refusal, lock cancellation of pending rotation, and fresh debounce on unlock.
JavaScript syntax validation passed and owner schema compilation succeeded.
The orderly restart returned to the selected clean root with GNOME and the
Power/display and rotation controllers running. Tablet Controls 7 reported
enabled with no extension error. The owner confirmed both brightness control
and Rotation Lock work, but reported delayed brightness changes during slider
movement. The existing 200 ms trailing debounce waits for movement to stop;
improving that scheduling remains separate work. The saved brightness after
restart was the owner's subsequently selected 90%, not the temporary 83% test
restoration.

The owner then reported lost touch. GNOME still answered its control bus and
the display was neither locked nor blanked. MyPaint was not running. A bounded
administrator check queried only active tracking-ID counts on the exact known
`sec_touchscreen` event5 device: zero contacts. The private `xwayland-touch:14`
bridge was enabled and had the expected direct multitouch capabilities.
`tools/reset_nested_touch.py --reset` disabled and immediately re-enabled only
that private virtual touchscreen, then verified its identity and enabled state.
It does not disable physical input, grab/inject events, record coordinates,
change S Pen configuration, or restart the session. Physical touch recovery
is not yet confirmed; the root cause is not assigned. This is a manual guarded
diagnostic, not an automatic reset loop or packaged startup workaround.

The owner's follow-up indicated pen motion still positioned the cursor and
finger contact hid it, but pen clicks also failed. This supports input reaching
part of the stack, not proof that physical events or GNOME dispatch are all
correct. No stuck virtual button was reported by a bounded query. The touch
re-enumeration was followed by GNOME's keyboard handler accessing an already
disposed `MetaInputDeviceX11`; do not treat that reset as a durable repair.
The exact old managed GNOME tree was stopped gracefully, leaving Weston,
networking, and hardware services running. The normal guarded launcher started
a fresh software-rendered managed session. Its startup password lock was
verified; authentication was not bypassed. Physical touch/pen click acceptance
after this session restart remains pending.

Follow-up: the owner confirmed login and brightness control, but reported another
input failure when opening the app menu. A separate bounded instrumented replay
after managed-session replacement worked; the diagnostic was then disabled.
See the [app-drawer input report](app-drawer-input-regression-20260915.md) for
current acceptance and the deliberately unassigned root cause.

All 267 tests subsequently completed (263 passes, four skips). New manual-reset
tests cover read-only default, ambiguity refusal, active-contact refusal,
already-disabled refusal, exact virtual-device targeting, and attempted
re-enabling even when disabling times out. On-device read-only validation of
all 14 staged release packages passed their exact name/version/hash checks and
private stock-package permissions. The temporary package bind was read-only
and unmounted on completion; no offline install or live-root identity audit
was attempted.

The tablet's DHCP address changed at this restart. Network SSH and the view-only
screen tunnel were restored after checking the dedicated SSH server key matched
the previously pinned key; strict host-key checking was retained. No private
SSH configuration or key is included in this repository.

Pen pressure investigation is deferred while the input regression is checked;
no new metadata experiment was applied.
