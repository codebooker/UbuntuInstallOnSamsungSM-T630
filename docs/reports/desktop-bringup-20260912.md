# Native Ubuntu graphical bring-up, 2026-09-12

**Historical RAM stage.** See `persistent-install-20260912.md` for subsequent
authorized internal installation, reboot status, and an important backup
correction: generated Netplan credentials were present in the original snapshot.
Use only the new `-sanitized.tar.gz` backup, not the now-deleted TLS original.

This follows the first BOOT/VBMETA flash. **No further flash, repartition, or
internal filesystem write was performed in this session.** Ubuntu still lives
in RAM under `/run/ubuntu`, with the stock Samsung kernel and diagnostic PID 1.

## Working results

- Ubuntu 24.04.5 ARM64 userspace; Weston 13.0.0 software-rendered desktop.
- Visible purple desktop verified by a captured frame, followed by owner
  reports of actual pen/finger interaction. No GPU acceleration claim.
- Terminal works after separately binding `/dev/pts` into the chroot.
- Finger touch and pen loaded from **exact T630XXSBDZE3 stock modules and
  firmware**, extracted from the user's firmware ZIP. No cross-model drivers.
- Wacom coordinates corrected with the `[libinput] left-handed=true` rotation.
  Owner confirmed correct pen position and tip clicks.
- Owner confirmed finger alignment and taps after applying
  `LIBINPUT_CALIBRATION_MATRIX=-1 0 1 0 -1 1`.
- Owner reported pen click-and-drag still failed. The v4 workaround below is
  running and its activation is logged; physical drag confirmation is pending.
- Wi-Fi initialized with cnss2/qca_cld3_wlan (actual module name `wlan`).
  Firmware identifies WCN6850. `wlan0` is the primary managed interface.
- Owner selected [redacted Wi-Fi network] and entered its password **on the tablet**, through a
  touch-friendly GTK window. Password was never passed in process arguments
  or copied to this report. Input-event recording was stopped and its temporary
  recording removed before further credential entry.
- NetworkManager reports `wlan0:connected:[redacted Wi-Fi network]`; native Python verified
  **HTTPS https://ubuntu.com returns HTTP 200** after fixing DNS.
- Battery last checked 29%, charging, 29.1°C.

## Required compatibility fixes

`tools/t630_drm_compat.c` is a process-local LD_PRELOAD library, compiled with
Ubuntu's native GCC. The successful runtime file is
`/run/ubuntu/tmp/t630-drm-compat-v4.so`. The verified snapshot contains the
previous v3 at `/usr/local/lib/t630-drm-compat.so`; overlay/recompile current
source when restoring.

1. Samsung's DRM planes report duplicate fourcc format entries (AB24 and NV12).
   Stock Weston asserts. The wrapper removes repeated format entries only.
2. Weston initially selected CRTC 186. Restrict resource enumeration to the
   physically tested first CRTC 113 on this device. The root cause of the black
   frame was subsequently isolated to timestamps, so the CRTC restriction is
   conservative, not proof that other CRTCs are intrinsically unusable.
3. **Samsung's page-flip events contain zero timestamps.** Weston consequently
   freezes its initial fade at black. The wrapper substitutes receipt-time
   CLOCK_MONOTONIC for zero timestamps only. This is approximate presentation
   timing, not a claim of hardware-accurate presentation timestamps.
4. Use `WESTON_DISABLE_GBM_MODIFIERS=1`, Pixman rendering, DSI-1 preferred mode,
   and `transform=rotate-90`. Disable the fictitious Virtual-1 connector.
5. Weston 13's desktop-shell move handler searches `seat->tablet_tool_list`,
   but the input backend puts non-unique pens on `tablet->tool_list`. Samsung's
   integrated pen has no MSC_SERIAL. The v4 library interposes the uniqueness
   query only for calls from libweston-13, placing this built-in pen on the
   seat-level list. This is a device-specific ownership workaround, not a claim
   that the pen has a real unique ID. Physical drag validation is pending.
   A non-maximized terminal is open for testing; Weston intentionally refuses
   window moves for maximized/fullscreen windows.

The successful rendered frame is `weston-clock-capture.png`; the earlier
`weston-first-capture.png` is black and documents the failure, not success.

## Input details

- Touch: `/dev/input/event5`, `sec_touchscreen`, native axes 1200x1920.
- Virtual DeX touchpad: event6, ignored by the Ubuntu input rule.
- Pen: event7, `sec_e-pen`. Kernel omits axis resolution, making libinput refuse
  it initially. The local udev rule supplies 100 units/mm for ABS_X and ABS_Y;
  libinput then reports approximately 135x217mm and tablet capability.
- Input rules: `ubuntu/99-t630-input.rules`.
- **Do not use echo with firmware_class.path.** Its module parameter retains
  the newline, so every firmware lookup fails. Use `printf '%s' PATH`.
- Firmware versions matched; Wacom explicitly logged matching 0x275 plus CRC
  and skipped firmware update. First failed probe generated a regulator warning;
  successful re-probe after correcting the path registered the input devices.
- Do not point the firmware search directory at every stock firmware file:
  unrelated IPA retries then repeatedly attempt an unsuitable image. The live
  search path `/run/input-firmware` exposes touch files and Wi-Fi subdirectories.

## Runtime and package setup

- Ubuntu packages were selected by native apt, downloaded on Mac and checked
  against SHA256 values in authenticated noble/noble-updates package indexes.
  Both InRelease signatures were verified with the Ubuntu archive keyring.
- Added Weston, seatd, udev, libinput tools, GCC/headers, NetworkManager,
  wpasupplicant, native Python/GTK, fonts and their dependencies in RAM.
- glibc advanced to 2.39-0ubuntu8.9 when installing matching development headers.
- `policy-rc.d` returns 101 to stop package installs from automatically starting
  services in the diagnostic chroot. Services needed here were started explicitly.
- Root directory must be mode 0755, not the diagnostic shell's default 0700.
  Mode 0700 prevented privilege-dropped D-Bus from reloading configuration.
- `SYSTEMD_IGNORE_CHROOT=1` is needed for udevadm trigger/reload, not for running
  udevd itself. Seatd runs with `SEATD_VTBOUND=0` because kernel VT support is off.
- Bind `/dev`, `/dev/pts`, `/proc`, `/sys` separately; create `/dev/shm` tmpfs.
- NetworkManager's default systemd-resolved mode points at an absent resolver.
  `ubuntu/90-t630-network.conf` selects `dns=default` and `rc-manager=file`.
- Set the tablet's wall clock from the Mac before testing TLS. The diagnostic
  boot started with a 2021 wall clock.
- BusyBox can prefer its own applets even for bare commands after `chroot`.
  Use absolute Ubuntu paths, e.g. `/usr/bin/dpkg`, `/usr/bin/ps`, `/usr/bin/env`.
- Native `apt-get update` now succeeds (exit 0, 16.5MB fetched), with signature
  verification intact. The diagnostic mdev default had changed `/dev/null` to
  root-only 0660, breaking apt-key's privilege-dropped shell. Standard character
  devices are now 0666; `ubuntu/mdev.conf` prevents that regression in RAM.
- Native online installation of chrony, dmz-cursor-theme, librsvg2-common and
  dependencies succeeded. These packages are newer than the saved snapshot.
- Chrony is running with `ubuntu/chrony-ram.conf`, selected Ubuntu's time
  source, and reports normal synchronization. NTP serving and network command
  ports are disabled; no RTC synchronization directive is enabled. A subsequent
  `ss -lntup` reported no TCP/UDP listening sockets. Native dpkg audit is clean.

## Next persistent-install boundary

- Read-only sysfs identifies `/dev/sda34` as PARTNAME=userdata, partition 34,
  major 259/minor 18, 226918360 sectors (116182200320 bytes). Revalidate identity
  immediately before any future write; do not identify it from the number alone.
- The running kernel has built-in ext4 and F2FS support. No internal filesystem
  was mounted during this check.
- Proposed next stage: reuse Android userdata for an Ubuntu ext4 root and create
  a separate stock-kernel BOOT candidate that starts it, retaining the physical
  USB diagnostic fallback. Preserve stock recovery/vendor_boot/DTBO/bootloaders
  and the existing partition table. No such write or boot candidate is completed
  yet. Obtain the owner's consequential-storage decision before proceeding.
- Cold boot, full systemd operation, GPU acceleration, suspend and a secure
  non-root daily-driver session remain unproven. A full stock restoration may
  be needed if the persistent experiment fails; restoration is not yet tested.

## Snapshot and restoration status

- A userspace snapshot has been built in RAM, excluding /dev, /proc, /sys,
  /run, /tmp, logs, apt caches/indexes, shell history, and **Wi-Fi credentials**.
- It includes exact stock vendor modules/firmware/config under `/opt/t630/vendor`,
  input rules, Weston settings, compatibility library and Wi-Fi entry program.
- Snapshot size: 462906200 bytes. Expected SHA256:
  `5aa43b557bdc6bcb226ccb768241d6e60ab4f157e93745f5dc180954b415411e`.
- Verified Mac artifact: `output/ubuntu-desktop-ram-20260912-tls.tar.gz`.
  Full SHA256 matched the tablet, gzip/tar listing passed, and excluded secret
  paths were checked absent. Manifest: `desktop-snapshot.sha256`.
- Both raw serial and large framed-base64 downloads failed. The `.incomplete`
  file is unusable; the misleadingly named `-verified.tar.gz` is a zero-byte
  failed attempt. Only the `-tls.tar.gz` artifact above is verified.
- Successful transfer used a one-file TLS server restricted to the Mac peer,
  with the self-signed certificate pinned through physical USB. The server
  shut down automatically after the copy; no transfer listener remains.
- DNS configuration, v4 pen workaround, mdev permission rules and the latest
  small package additions came after snapshot creation. Restoration must
  overlay those local changes rather than assuming they are included.
- Snapshot restoration and boot-persistent installation are **not yet tested**.
- Do not mount/format Android userdata or flash another BOOT without the next
  consequential-storage decision being made with the owner.

## Serial transport lessons

- `/dev/cu.usbmodemT630BRINGUP0011` remains the physical USB management path.
- Long interactive commands exceed BusyBox's line-editor buffer. `Link.run`
  now stages scripts in RAM when their encoded size exceeds 700 bytes.
- Raw binary upload still verifies SHA256 successfully, including 542MB vendor
  data. Raw download is NOT reliable with the current end-of-transfer handling;
  large framed base64 also failed. Use a narrowly scoped, certificate-pinned
  TLS transfer over the now-working Wi-Fi for large downloads.
- Never run two serial commands/transfers concurrently. No tool output is proof
  of remote success without checking its `REMOTE_EXIT` and relevant evidence.
