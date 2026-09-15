# GNOME first-boot host acceptance (2026-09-14)

## Problem and result

The physical first-boot preview initially failed to show any keyboard. The
development tablet had retained its stock-keyboard recovery preference, and
GTK 3 on the Weston 13 host selected a text-input protocol Weston does not
provide. Selecting the packaged `t630-wayland` bridge and forcing Maliit before
an owner exists restored a functional recovery path. The owner physically
confirmed touch entry, but correctly rejected its different keyboard as an
end-user installer experience.

The final preview now runs the GTK setup frontend inside a disposable GNOME 46
host. GNOME Shell and its session services run as the locked `nobody` account;
their runtime, home, cache, configuration, and D-Bus state are all below
`/run/t630-first-boot-session`. The root frontend connects only as a Wayland
client and retains the already-audited password/account backend. No temporary
human account, home directory, password, or image identity is created.
The shell has no supplementary groups, no capability bounding/ambient set, and
`NoNewPrivs=1`. Access to the outer Wayland socket is temporarily assigned to
`nogroup`; teardown restored the exact prior directory/socket groups and modes.

The physical panel showed GNOME's normal on-screen keyboard and accepted touch
text in the account fields. The keyboard, Shift, Enter, Backspace, and hide key
are therefore the same implementation used after setup, rather than a visual
approximation in the recovery compositor.

## Rotation and lifecycle

The first host used a fixed 1920x1200 rootful Xwayland window and exposed the
same stale-host-window defect found during early desktop work when the tablet
was turned to portrait. A dedicated unprivileged resize helper now follows the
validated Weston rotation state. It changes the Xwayland host mode and nested
Mutter monitor together. Physical evidence from this run was:

- transform 2: Xwayland and GNOME both changed to 1200x1920; the account form
  and GNOME keyboard filled the portrait panel without exposing Weston;
- transform 1: both returned to 1920x1200 when the owner rotated back;
- terminating preview removed the temporary shell, Xwayland, resize process,
  Wayland socket, and process group while leaving the normal owner GNOME
  session running.

A root-only, signal-safe rotation relay claims SensorProxy during true
ownerless first boot and writes only the existing bounded Weston FIFO. Sensor
startup has a narrowly scoped first-boot mode that skips the normal audio-ready
ordering wait because an owner audio session cannot exist yet. Ordinary sensor
startup retains its established audio ordering. A physical relay test applied
transform 1 and exited cleanly after SIGTERM.

## Package and health gates

The live development files were migrated into normal package ownership. A
pre-package local diversion for Weston/Maliit was converted to the
`t630-boot-runtime` diversion without stopping the working compositor. The
previously loose native helper files were also registered through the existing
hash-pinned `t630-native-userspace` package. `dpkg --audit` is empty.

Current deterministic artifacts at `SOURCE_DATE_EPOCH=1700000000` are:

- `t630-first-boot_0.1.1_all.deb`:
  `3b3adf74477f0402e30d3d443dcd49068eb2bf139afa83a2f4c4e346bb18a14e`
- `t630-desktop-runtime_0.1.1_all.deb`:
  `5895d74c2b8a793b62e7eabf6e8f45e55cbc09f2b1d7637a55b3810079feb7f1`
- `t630-hardware-runtime_0.1.2_all.deb`:
  `51d39bb832461513f95db7bc97efd7cdb3905975a2edd6b06a7c80ff08379694`
- `t630-boot-runtime_0.1.0_all.deb`:
  `70c75d8b0e68c48fbc8366bbe0432df0e4a1acde99cde096ae05902f51bdde9e`

All 231 repository tests passed with four documented skips. After the GNOME
installer sessions and both rotations, Weston, owner GNOME, Wi-Fi, Bluetooth,
speaker and microphone defaults, device permissions, battery reporting, and
the accelerometer remained healthy. The targeted kernel log contained zero
panic, Oops, KGSL-fault, watchdog, overload, or MSM video error markers.

The physical clean-root run completed every packaged page without a pre-existing
human account, connected to Wi-Fi, created the selected owner, and reached that
owner's GNOME password lock. It caught and corrected four package-boundary
issues: desktop-runtime creates the system-only `t630-owner` group before Weston
starts, hardware-runtime explicitly depends on `wpasupplicant`, hardware-runtime
ships the `mdev.conf` consumed by its permission repair, and desktop-runtime
ships its X11 recovery guard. New-account GNOME settings can report an empty
extension list as `@as []`; the owner migration now parses that typed form and
installs the normal Tablet Controls extension. The installer frontend also uses
Adwaita dark mode for future runs.

The first cold boot of the personalized result automatically started the new
owner's GNOME session and reconnected `Wharf`. It then caught two hardware-only
clean-root omissions: Bluetooth startup circularly required its generated
address before invoking the generator, and the reproducible pd-mapper had both
the wrong QRTR runtime dependency and no explicit map-directory compatibility
patch for Samsung's non-remoteproc kernel.

The second cold boot generated the Bluetooth address, powered BlueZ, kept the
patched mapper running, and registered the real Qualcomm sound card. It exposed
three final minimal-root assumptions: the speaker-protection verifier and
`pactl` were absent, and Xwayland could still crash in Mesa's explicit DRM path
despite `XWAYLAND_NO_GLAMOR=1`. The corrected packages now include the verifier,
depend on `pulseaudio-utils`, and disable Xwayland GLX. The live repaired session
then held its complete managed process chain and user runtime; GNOME dark mode,
keyboard, Wi-Fi, the speaker and microphone defaults, accelerometer, Bluetooth,
battery, package audit, and a zero-count targeted kernel-fault scan all passed.
The final no-intervention cold boot exposed that nested Mutter starts a second,
internal Xwayland independent of the explicit GLX-disabled host. That process
entered the same Mesa path and left the recovery desktop visible. Disabling the
internal Xwayland for the Wayland-native installer and owner sessions fixed the
actual failure. Boot v4 then started the complete managed process chain,
verified the GNOME password lock, showed no recovery terminal, and reconnected
`Wharf`; speaker and microphone defaults, accelerometer, Bluetooth, dark mode,
keyboard setting, package audit, boot readback, and the targeted fault scan all
passed. Return-to-stock rehearsal is the remaining release gate.
