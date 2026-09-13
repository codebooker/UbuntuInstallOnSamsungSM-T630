# Desktop and keyboard — 2026-09-12

## Current result

Native Ubuntu 24.04.5 remains on the SM-T630's userdata filesystem. No boot,
recovery, driver, calibration or partition changes were made during this work.
Wi-Fi SSH and the loopback-only screen service remain available. Battery rose
from 6% to 14%, Charging; the owner's brightness setting is preserved.

Installed Thunar 4.18.8, Mousepad 0.6.1, Xfce Terminal 1.1.3, htop 3.3.0 and
sudo 1.9.15p5 (Ubuntu's security-patched package). Package audit is clean and
sudoers validates. Normal account `tablet` is UID/GID 1000 with its own home and
session bus. The owner entered a password in a masked local window; status is
now P and the user belongs to sudo. The physical screen showed a successful
owner-run `sudo apt update`. No password was supplied by the assistant or stored
in this project. SSH remains pinned-host, key-only root administration.

Top-panel launchers and the Tablet controls window open files, editor, terminal,
Wi-Fi setup and password setup. Controls report charging, connection and storage,
and provide a bounded brightness slider. GTK uses larger fonts and dark styling.

The stock Samsung tmpfs does not support POSIX ACLs. Display access is instead
root:tablet 0710 on `/run/user/0` and root:tablet 0660 on the Wayland socket.
Normal apps use their own 0700 `/run/user/1000` and connect to the absolute
Wayland socket path. Root's home remains inaccessible to them. The compositor,
keyboard and administrative controls still run as root: this is a prototype,
not a hardened multiuser desktop.

## Keyboard

Maliit 2.3.1-5build2 / framework 2.3.0-4build5 replaces weston-keyboard.
QtWayland 5.15.13 supplies the inputpanel-shell plugin. Qt Quick uses software
rendering and Material dark controls. Maliit's device setting is `tablet`,
English is selected and unavailable haptic feedback is disabled.

`ubuntu/t630-keyboard` is deployed as `/usr/libexec/weston-keyboard`; the
original is preserved by dpkg-divert as `weston-keyboard.t630-stock`.
The launcher must inherit Weston's WAYLAND_SOCKET connection: an arbitrary
manually launched input-method client cannot bind Weston's privileged protocol.
`/etc/t630/keyboard-mode` is `maliit`. Nonzero failures are rate-limited before
Weston respawns the launcher; there is no automatic switch to the stock client.
The retained stock mode is for deliberate cold recovery only.

Maliit's packaged Shift/Enter icons were absent from the initial installation;
its lowercase Backspace icon name also contains an upstream spelling error.
`ubuntu/install-keyboard-icons.sh` installs local hicolor aliases from Ubuntu's
Breeze icons, including the typo alias; no package icon files are overwritten.
`libqt5svg5` supplies SVG loading. All three key symbols are visually present.

`ubuntu/MaliitKeyboard.qml` adds an explicit Hide keyboard button above the keys
and a long-press hint. The packaged Keyboard.qml is retained with dpkg-divert
under its `.t630-stock` suffix. This override must be reviewed when upgrading
Maliit, not assumed compatible with all future releases.

### GTK compatibility

Ubuntu's GTK3 built-in Wayland IM module speaks text-input-v3, whereas Weston 13
offers v1. `tools/t630_gtk_im.c` implements an opt-in v1 bridge, built natively
with `tools/build_gtk_im.sh` against Ubuntu's wayland-protocols definitions.
It is installed as `/usr/local/lib/im-t630-wayland.so`, selected only by our
normal app launcher and password UI through a private module cache. Stock GTK
modules are untouched. It supports basic commit/preedit, backspace/Enter key
events and surrounding text; hardware keys retain GtkIMContextSimple handling.
Password/PIN fields send hidden/sensitive hints and no surrounding text.
Advanced IME selection/replacement, prediction and all third-party apps have
not been comprehensively tested. No key or entered-text logging was added.

### Evidence and limitations

- Owner typed ordinary text, numbers, a newline and “hello world from the spen”
  into the initial Maliit test window. That is owner interaction, not an
  automated-test pass. Source inspection explains why stock weston-keyboard
  lacked pen-key support: it registers touch/pointer handlers but no tablet
  tool handlers.
- Screenshots `maliit-pen-check.png` and `maliit-dark-ready.png` record initial
  text entry and the final dark layout with visible Shift, Backspace, Enter
  and Hide keyboard controls.
- The earlier strict `tablet` test did not pass its expected-string assertion;
  the owner was using the field interactively. Do not label that report as a
  completed automatic key-sequence test.
- Synthetic pen/touch helpers were not a reliable verification of the final
  keyboard button locations. Do not reuse guessed coordinates for terminal
  commands or password fields. The owner explicitly confirmed that the final
  Hide keyboard button works with the physical S Pen.
- A keyboard-only restart briefly triggered a stock fallback crash loop.
  Weston stopped respawning it. With only terminal/controls open, the desktop
  was refreshed (not the tablet rebooted), restoring Maliit and launchers.
  Automatic stock fallback was removed. No reboot persistence test was done
  after this desktop update; cold compositor startup did launch Maliit.
- The sanitized root backup predates this update. It remains a recovery
  snapshot, not an up-to-date clone. Do not include credentials in a new backup.

## Shutdown and recovery

The persistent stop helper now terminates processes rooted specifically at
`/run/ubuntu`, then unmounts normally. Its matching copy was placed in the outer
RAM recovery environment. It aborts on unmount failure rather than forcing an
unclean restart. This expanded desktop shutdown path has not been reboot-tested.

For keyboard recovery, use SSH/USB. Keep the active mode as maliit and inspect
`/run/t630-maliit.log` and `/run/weston.log`. Do not repeatedly kill the compositor
while user documents are open. If a full rollback is needed, restore the two
dpkg-diverted originals in a controlled stopped desktop, retaining local overrides
for diagnosis; the stock keyboard's pen limitation will return. Never run the
S9 Ultra install/update/partition scripts on this SM-T630.

Installed SHA256:

- keyboard launcher: b1acedc37323bca40212fe0556201d53f47a99facdf4e43bbefcd0cd60b14692
- Keyboard.qml: eae05cd9eb073ce99ea9647140f7de0a76a2ccf0ac0fed0a8344c28a5537b591
- GTK IM module: 902a03b3fdde8c8aa430d7f5eb623c2c4873cb3ea0810f85de85725eb0667b0a
- stop helper: 127af095d89a66fccf63e6f439b8cc73ae22ad940a8c47bf19a4bebc03eaf6ca

## Software direction from the supplied S9 Ultra project

Reviewed its README and [Ubuntu userspace documentation](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/blob/main/docs/ubuntu-userspace.md).
That project uses GNOME 46/Wayland/GDM, GNOME's own on-screen keyboard and
control center, normal-user onboarding, NetworkManager, PipeWire/WirePlumber,
and a reproducible Ubuntu package manifest. Those are relevant design choices
for us, not model-specific firmware to copy.

The next desktop direction should be a tested normal GNOME session rather than
expanding the Weston test shell with more custom desktop replacements. Reuse
upstream Ubuntu components and keep any necessary device adaptation small and
reproducible. Test GNOME nested or as an alternate session before replacing the
working display path. Preserve SSH/USB rescue independently.

Important differences: our stock kernel lacks a proven Mesa acceleration path;
Weston currently renders in software with a device-specific DRM compatibility
shim. PID1 is still outer BusyBox; `/sys/fs/cgroup` exists but no cgroup hierarchy
is mounted, and logind/systemd user sessions are not provisioned. GNOME package
dependency simulation succeeds, but that is not a working GNOME session.
Its GDM/systemd/graphics requirements need deliberate validation; copying its
package list alone is insufficient. No GNOME installation or startup replacement
was performed in this keyboard fix.
