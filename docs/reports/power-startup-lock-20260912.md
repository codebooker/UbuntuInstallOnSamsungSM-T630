# Persistent lock and physical Power setup

Continuing after owner confirmed the deferred-keyboard swipe fix worked.

## Installed changes

- `/etc/t630/login.enabled` selects the existing managed elogind/GDM session at
  every startup. `login.disabled` opts out; old one-boot test flag still works.
- Managed GNOME sessions enable the real password lock and suppress GSD's
  competing Power action. Unmanaged recovery sessions leave locking disabled.
- `/etc/t630/lock-on-start` requests the standard GNOME lock once its session
  bus is ready. Normal-user helper checks both ScreenSaver Active and real
  elogind LockedHint. Bounded40s startup check, no password handling. This is
  a startup desktop lock, NOT a native GDM greeter or a hardened recovery boundary.
- Root `/usr/local/sbin/t630-power-button` reads only the unique `qpnp_pon`
  device, filters KEY_POWER116, no input grab, no arbitrary endpoint/listener.
  Short release locks with GNOME, verifies Active and actual-session LockedHint,
  then writes only validated panel0-backlight brightness0. Refuses to blank
  without a verified lock. Another short press restores saved brightness and
  sends a modifier-only wake event; it NEVER calls an unlock/deactivate method.
  Long presses/repeats are ignored, no suspend/shutdown call. Root-only runtime
  saved brightness file, restoration on orderly exit and next monitor start.
- Backlight control: `/sys/class/backlight/panel0-backlight`, max306, original
  brightness255. The separate `panel` node has max0 and is not touched.
  Driver actual_brightness incorrectly reads0 even when lit; don't use it as
  proof of physical screen-off. Physical owner confirmation remains required.

## Verification before restart

- Python helpers compile and shell syntax checks pass.
- Power helper `--check` validated install ID, input identity and panel.
- `--test-cycle` verified password lock, blanked for3s, restored255 in finally.
- Monitor PID2201 comm`t630-power-key`, no other power input consumers modified
  except GSD's static binding suppressed; elogind's verified policy is ignore.
- Startup-lock helper ran as normal user and verified lock metadata.
- Requested user test of Power off/on and password requirement, pending.
- Backup of previous autostart/session launchers:
  `/usr/local/share/t630/backups/power-persistence.2VIgUO` on tablet.
- Persistent flags installed; clean reboot dispatched using unchanged verified
  stop helper SHA2569146f3cdd0f47460aaba1e062a28bddd1c8cb70fd5aac66e3f40c545d1975437.

## Persistent reboot verification

- Clean boot ID `0b23c83e-fc32-4e71-9b54-d11cc600b99e` brought back Wi-Fi,
  SSH, the view-only screen service, managed GNOME and the Power monitor.
- Startup log confirms `GNOME startup password lock verified.` Normal-user
  ScreenSaver GetActive returned true and elogind session c1 LockedHint=true.
- `t630_speakers` exists and is unmuted. Battery reports Charging, 21% at the
  later check. This verifies services/status, not a new audible playback test.
- Physical Power confirmation remains pending; monitor has not logged an
  off/on action yet. Do not count the automated backlight cycle as this test.
- Set local timezone to America/New_York, matching the owner's Mac context.
  Previous timezone files backed up at
  `/usr/local/share/t630/backups/timezone.2qIHYu` on the tablet.
- Checked the store authorization path without opening a password dialog or
  unlocking. GNOME's built-in session-wide polkit agent still fails registration;
  the previously installed process-scoped helper successfully registers and
  remains running for normal-user GNOME Software after the managed-session boot.
  A noninteractive package-install policy check exits2, explicitly requiring
  authentication. No polkit policy, PAM, passwords or privileges changed.
  This checks registration/auth requirements, not a new user-authenticated
  installation. The earlier Contacts/Inkscape authentication tests predate this
  managed boot.

## Scope / remaining work

Software rendering remains selected via gpu.disabled following a real KGSL hang.
Power blanking does not suspend the tablet or establish battery-saving sleep.
Outer Weston recovery desktop and unauthenticated lab USB recovery still exist.
Do not claim full-device login security or storage encryption. Startup lock is
applied after GNOME starts, not before a user session exists. A failed prerequisite
can still leave the deliberately retained lab recovery desktop available.

Recovery if a monitor is killed abnormally while blanked: its next start reads
the root-only saved brightness state and restores it. USB/root recovery remains
available; don't force reboot or touch partitions to recover the backlight.
