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
   without resetting chosen paths. The exact-device filesystem-ready helper
   produced fast warm boots but is not used by normal startup: repeated
   charger/LPM cold boots proved that Samsung's kernel skips cfg80211 regulatory
   initialization in that mode and panics in `handle_reg_beacon` on the first
   scan. Boot v12 detects charger mode before consuming the one-shot selector
   and performs a clean normal reboot. The saved network is MAC-bound to the
   real `wlan0` client rather than secondary/P2P interfaces. Full Power Off
   while USB-powered then passed GNOME, the stock CNSS timeout, first scan,
   DHCP, and zero-fault health checks.
2. Build and exercise a reproducible installer and complete stock-recovery path.
   The desktop runtime, source-only hardware orchestration, Qualcomm sensor
   stack, ARM64 compatibility packages, isolated GDM/elogind password-login
   runtime, and local-only stock-assets package are reproducible, including the
   audio protection-domain mapper and redistributable camera runtime.
   The reproducible AVB-verified persistent boot image uses the current module-
   compatible kernel and initramfs; its guarded write, two cold boots, full
   shutdown, automatic remote startup, and health checks passed. Clean-root
   installation completion and the return-to-stock rehearsal remain. The new
   one-command ARM64 host builder assembles a fresh ownerless root, applies and
   audits the exact release set, emits a deterministically serialized private rootfs archive
   with numeric ownership/ACLs/xattrs, and seals the accepted dual-layout BOOT
   input without opening any device. A separate recovery verifier requires the
   exact DZE3/XAR BL/AP/CSC/HOME_CSC set and can stream-check every ZIP CRC and
   Samsung tar MD5 without extracting the 6.4 GB factory package. The remaining
   RAM-only USB-serial stager now verifies the sealed bundle locally, streams
   files at constant host memory cost, and rechecks all hashes on the exact
   tablet without any block-device write. A tablet-local path now avoids a
   second multi-gigabyte host copy. The complete 1.2 GB private bundle was
   copied into bounded recovery RAM and verified there on the physical tablet.
   A private recovery-tool builder and two-phase installer now implement exact
   `linuxroot` formatting and extraction with preserved ownership/ACLs/xattrs,
   post-extract identity/package checks, unmounted read-only fsck, one-attempt
   locking, explicit typed authorization, and no automatic reboot. After the
   working system was stopped and `linuxroot` was genuinely unmounted, the full
   physical read-only gate verified every protected partition and the isolated
   recovery runtime without formatting. The fresh 0.1.19 bundle and its exact
   dual-layout partition/BOOT guards passed the same physical RAM-stage and
   unmounted read-only gate on 2026-09-17. Remaining gates are the explicitly
   authorized clean-install/first-boot run and stock-return rehearsal. Boot v3
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
   The 2026-09-16 package refresh also removed stale exact dependencies left by
   incremental development. Component packages use compatible minimum versions,
   while `t630-release-base` 0.1.19 remains the single exact-version lock for a
   release. The live personalized root now passes `dpkg --audit` and
   `apt-get check` after a clean reboot; the login runtime rebuild is
   byte-identical. See the
   [package consistency report](reports/package-dependency-repair-20260916.md).
3. Pen-friendly handwritten notes and drawing. Xournal++ and MyPaint are now
   installed as native ARM64 apps on the personalized clean root; both launch
   inside GNOME, and an Xournal++ page shows continuous physical handwriting.
   Krita 5.2.2 explicitly rejects native Wayland and is deferred alongside the
   legacy-X11 issue. The physical pen sensor and the corrected GTK test before
   GNOME now confirm varying pressure. Native GTK inside GNOME subsequently
   received 310 physical pen samples (normalized pressure 0–0.800534) and 147
   finger events in the explicitly enabled real-event/source-axis trial.
   The earlier proximity preloads were removed after failing acceptance and
   causing a hover regression.
   A matching-source, isolated diagnostic Mutter build now starts safely to
   inspect tool registration and focus without injecting events. See the
   [pressure-path report](reports/pen-pressure-path-20260915.md). Native GTK pen
   delivery is measured and the owner confirms MyPaint pressure response, but
   excessive force and multi-second drawing lag remain. A mathematically
   verified 2× app curve worsened perceived force and was reverted to identity.
   Simple GTK event delivery measured 4 ms median/58 ms maximum; headless
   stock-brush rendering and single-layer composites were fast, not full GUI
   latency acceptance. Investigate the live queue/redraw path before tuning
   sensitivity further. Physical hover-out,
   restart/rotation/lock regressions and safe persistence remain unaccepted.
   MyPaint's first-stroke GUI crash was reproduced in an isolated headless test:
   four rendering workers segfault, one worker passes. Its optional launcher now
   serializes only MyPaint; responsive physical drawing remains to verify. The
   isolated upstream-GIL-fix extension subsequently passed both thread settings
   in bounded headless tests, without a small-workload speedup or GUI promotion.
   Live timing caught up to 11.685 seconds of queued stroke delay despite fresh
   pen delivery and short callbacks. A steady app-only high-idle run with the
   same reported brush bases reduced queue age from 7.405 s median/11.404 s p95
   to 41/81 ms while canvas redraws continued. The exact-version normal adapter
   now applies that priority before MyPaint starts; it does not change ordinary
   input priority, GTK globally, or the normal launcher for other apps. The
   owner reported much better pressure and only slight remaining lag, while
   Xournal++ had no perceptible lag. The MyPaint preset was stock
   `classic/short_grass`, which deliberately uses slow tracking 2.0. Its real
   per-device stylus clone—not merely the general selected-brush preference—was
   backed up and changed to stock pressure-aware `deevad/ballpen`, whose two
   slow-tracking values are zero. That control measured 28/49 ms queue age at
   priority 100 and 26/43 ms at priority 0, with sub-millisecond stroke callbacks
   and fast redraws. The exact-version normal adapter now uses 0, with both older
   helpers retained for rollback. The owner reports the resulting normal app
   feels better; longer-session acceptance remains pending. The
   drawing app is no longer automatically pinned because GNOME hides favorites
   from the app drawer.
   Xournal++'s initial `touchDrawing=false` setting prevented finger ink but
   still allowed the palm to pan the page. Its distinct one-second internal hand
   recognition was enabled by a one-time, choice-preserving seeder, but the
   owner confirmed that this app-level trial still moved the paper. Udev had
   assigned the integrated touch and pen separate libinput device groups. The
   exact devices now share `t630-integrated-pen-touch`, but libinput's partial
   rejection region still let the page move. A guarded root helper now reads
   only the exact pen's tool-presence key and disables only the exact touchscreen
   for the full proximity interval, without grabbing or logging input. The owner
   confirms palm rejection works before and after an orderly restart; the guard
   and normal enabled-touch state returned automatically.
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

Native stock Android 15 is the accepted application path. It uses its own
encrypted 44.2 GiB F2FS `userdata` partition and the stock Adreno stack, while
Ubuntu remains on the 64 GiB `linuxroot` partition. The Ubuntu and Android
touchscreen switchers completed a physical round trip without altering either
data partition or any protected neighbor of BOOT. Android retained Play
services, Samsung Notes, S Pen input, and the rooted fixed-command switcher;
Ubuntu returned on its exact accepted BOOT with GNOME and its reverse switch
ready.

The rejected CPU-rendered Waydroid packages, images, owner data, launchers,
backups, and kernel trials have been removed from Ubuntu. Its source and reports
remain only as historical evidence. Remaining Android work is limited to
repeated cold-switch endurance, forced refusal/failure cases, recovery rehearsal,
and including both switchers in the final clean-install acceptance. See
[DUALBOOT.md](DUALBOOT.md).
