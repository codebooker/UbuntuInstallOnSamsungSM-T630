# SM-T630 completion roadmap

## Current priority order

1. Remove the development account from device integration and implement the
   normal first-boot account flow. The account-neutral flow and reproducible
   `t630-first-boot` package are implemented; the account-neutral GNOME asset
   migration and reproducible source-only desktop runtime package now work.
   The physical preview uses a RAM-only, unprivileged GNOME installer host, so
   the normal GNOME keyboard and both landscape/portrait layouts have passed.
   A guarded one-shot physical boot completed the packaged wizard from the
   ownerless clean root, connected Wi-Fi, created the selected owner, and reached
   that owner's GNOME password lock. It exposed and fixed the pre-account owner
   group, Wi-Fi backend, device-permission configuration, owner-settings parser,
   and desktop recovery payload gaps. The installer is dark by default. A cold
   boot of the personalized result automatically launched owner GNOME and
   reconnected Wi-Fi. Two cold boots exposed and corrected Bluetooth-address,
   audio-mapper, speaker-verifier, `pactl`, and Xwayland packaging assumptions.
   The third no-intervention cold boot passed the complete managed-session,
   password-lock, Wi-Fi, audio, sensor, Bluetooth, package, and boot-image
   checks. Normal owner startup no longer exposes the recovery terminal or
   waits for its three-second mapping delay. The backend creates and validates
   the device's unique machine ID only after boot, preserving a blank
   distributable image and unique Bluetooth identity. GNOME Settings is now an
   explicit package dependency, the dead default Utilities grouping is now
   suppressed before Shell initializes using an invisible empty-folder sentinel
   (the earlier post-start empty-list fix was incomplete), personal favorites
   are no longer reset on boot, Home/Recents mappings persist, and native Restart/Power Off
   confirmations reach the guarded orderly shutdown path. Owner wallpaper
   choices now persist, and an orderly system action returns to the personalized
   clean installation while an abnormal boot still falls back to the lab root.
   The next unattended orderly restart also passed automatic owner-only SSH and
   screen-feed startup. Standard owner document folders are now initialized
   without resetting chosen paths. Remove the 70-second CNSS startup wait by
   testing the driver's normal filesystem-ready/calibration ordering; a guarded
   probe is prepared, not yet integrated. Full Power Off remains a separate
   clean-root acceptance test.
2. Build and exercise a reproducible installer and complete stock-recovery path.
   The desktop runtime, source-only hardware orchestration, Qualcomm sensor
   stack, ARM64 compatibility packages, isolated GDM/elogind password-login
   runtime, and local-only stock-assets package are reproducible, including the
   audio protection-domain mapper and redistributable camera runtime.
   The reproducible AVB-verified persistent boot image uses the current module-
   compatible kernel and initramfs; its guarded write, two cold boots, full
   shutdown, automatic remote startup, and health checks passed. Clean-root
   installation completion and the return-to-stock rehearsal remain. Boot v3
   makes an incomplete ownerless setup cleanly recoverable; boot v4 retains
   that terminal only for ownerless or explicitly requested recovery boots. The
   account-neutral Weston/Maliit host runtime is now packaged with reversible distro-file
   diversions. An exact-version base metapackage prevents incompatible
   component combinations, and the guarded offline assembler installed the
   full package directory into a fresh, identity-clean Ubuntu 24.04.5 ARM64
   rehearsal root on the tablet. That clean root now also includes the verified
   native Firefox repository, GNOME Software/PackageKit, LibreOffice, and the
   normal desktop application set without Snap.
   The factory dynamic-partition parser now verifies and emits the exact
   read-only `system`/`vendor` mappings directly from physical or sparse
   `super`; the camera runtime physically passed with those mappings and its
   guarded shutdown removed them, eliminating the second per-user vendor copy.
   The four required APEX payloads and two narrowly patched binaries are now
   reconstructed locally with complete input/output hashes directly from the
   tablet's read-only stock `super`; they matched the working runtime
   byte-for-byte. Writable camera state regenerates without a seed.
3. Pen-friendly handwritten notes and drawing. Xournal++ and MyPaint are now
   installed as native ARM64 apps on the personalized clean root; both launch
   inside GNOME, and an Xournal++ page shows continuous physical handwriting.
   Krita 5.2.2 explicitly rejects native Wayland and is deferred alongside the
   legacy-X11 issue. The physical pen sensor and the corrected GTK test before
   GNOME now confirm varying pressure. Native GTK inside GNOME receives finger
   events but still has no accepted pen samples. The manual metadata/proximity
   trials were removed after failing acceptance and causing a hover regression.
   A matching-source, isolated diagnostic Mutter build now starts safely to
   inspect tool registration and focus without injecting events. See the
   [pressure-path report](reports/pen-pressure-path-20260915.md); genuine native
   GNOME pressure and safe persistence are not yet accepted.
   MyPaint's first-stroke GUI crash was reproduced in an isolated headless test:
   four rendering workers segfault, one worker passes. Its optional launcher now
   serializes only MyPaint; corrected physical drawing remains to verify. The
   drawing app is no longer automatically pinned because GNOME hides favorites
   from the app drawer.
   A separate MyPaint Wayland popup-grab freeze is under investigation. Its
   autosave cache was preserved before closing the stuck app; an experimental
   app-only adapter replaces quick chooser popups with existing dockable panels.
   Startup/tests pass and the owner confirms physical touch/S Pen recovery;
   the owner also confirms the bounded long-stroke and brush/color control check.
   Extended drawing sessions and the remaining pen acceptance gates are pending.
   A generated OpenRaster file now passes native archive/load/frame/settings
   checks, but pixel equality does not pass; GUI save/reopen is still separate.
   The missing launcher icon was corrected; the post-Home live screenshot now
   verifies MyPaint Drawing at the upper-left of the first app-grid page. A
   physical launch from that tile remains to verify. See
   [the pen follow-up](reports/pen-launcher-file-check-20260915.md).
   Evaluate notes/PDF annotation and drawing using
   the stable Wayland desktop. Verify continuous S Pen strokes, pressure,
   palm rejection, pen-button tools, portrait/landscape alignment, performance,
   and save/reopen after restart before adding accepted apps to the clean-root
   recipe. Current handwriting does not prove pressure or palm rejection works
   through the nested compositor.
4. Broader camera lighting/application tests and photo-flash integration.
5. Bluetooth headset playback, microphone, and reconnect testing.
6. Four-edge and post-resume sensor/rotation validation.
7. GPU stability and browser-video isolation.
8. microSD, USB host, GPS, NFC, and external-display coverage.
9. Android application support through a coherent kernel and matching module
   payload. This is deliberately last because changing the required namespace
   options invalidates every audited stock Samsung module.

Completed: automatic shallow suspend now passes unplugged idle entry, physical
Power wake, same-boot recovery, and sensor/Wi-Fi/audio restoration. The guarded
helper temporarily quiesces the SSC sensor bridge so its ADSP GLINK channel does
not immediately wake the tablet.

## End-user installer requirement

The release installer must not clone the development tablet's `tablet` account,
password, SSH keys, network credentials, machine identity, or runtime state. It
should install a generic Ubuntu system, then present a normal first-boot flow for
language, time zone, Wi-Fi, username, password, and optional accessibility and
privacy choices. Device integration belongs in packages or image overlays that
do not depend on a particular human username or UID. Recovery and a return-to-
stock path must be documented before the installation is called end-user ready.

The intended pages follow Ubuntu Desktop's normal order and terminology:
language, accessibility, keyboard, network, account/computer name/password,
time zone, and privacy/welcome. The result must use the person's chosen account
for GNOME, application data, authentication, audio, Waydroid, and remote access;
the current hard-coded lab account is not a shippable default. Ubuntu 24.04's
[release notes](https://documentation.ubuntu.com/release-notes/24.04/) say that
OEM installs are not supported by its desktop installer, so this image needs a
tested first-boot provisioning flow rather than a misleading OEM-mode shortcut.

The packaged backend first completed in the fresh rehearsal root using a
non-personal sample account: UID/GID 1000, password state, owner group, locale,
keyboard, time zone, hostname, and account-neutral desktop startup all passed.
The backend refused a second run, and the release audit correctly rejected the
personalized result. The later physical clean-boot run completed the same pages
with the normal GNOME keyboard, connected Wi-Fi, created the chosen owner, and
reached the new owner's password lock. Three subsequent personalized cold boots
now pass automatic startup; the final one also removes the visible recovery
terminal from the normal path.

## Android applications

The reference Tab S9 Ultra project uses Waydroid with an ARM64-only LineageOS
image. The SM-T630 already exposes binderfs, binder/hwbinder/vndbinder, ashmem,
overlayfs, cgroups, veth, bridge, and built-in IPv4 Netfilter/NAT support. Its
current Samsung 5.4 configuration lacks PID, IPC, and user namespaces, two cgroup
controllers, the Xtables CHECKSUM target, and the System V IPC dependency.

An isolation build proved that enabling the missing namespace and cgroup
features changes the module-version ABI. All 235 audited stock modules are
affected, so a boot-image-only Waydroid kernel is not a viable release path.
Android work is deferred until the native Ubuntu installation is complete and
the project can build and validate a coherent kernel plus matching module
payload. No Android image should be installed before that gate passes.
