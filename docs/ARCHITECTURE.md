# Port architecture

## Boot chain

The SM-T630 uses an Android boot image with header version 3. The tested design
keeps Samsung's exact downstream kernel and replaces only the generic ramdisk
with a small gzip-compressed initramfs. The first image boots a RAM-only BusyBox
environment and exposes a physical USB serial recovery shell.

The persistent prototype uses the same conservative boot structure, mounts the
Ubuntu ext4 filesystem from the existing userdata partition, and starts the
device-specific userspace. Recovery, vendor_boot, DTBO, the partition table, and
bootloader partitions are not replaced by the normal prototype path.

## Desktop stack

The internal Qualcomm DRM device drives Weston. GNOME runs as the unprivileged
owner selected at first boot in a managed, screen-sized nested session. Runtime
services resolve that account from `/etc/t630/owner` and the local password
database instead of assuming a username, UID, GID, or home directory. The
dedicated `t630-owner` group gates narrow camera, sensor, and rotation actions.
The rootful Xwayland
host is deliberately undecorated rather than protocol-fullscreen: Xwayland 24
disconnects if a fullscreen xdg-shell surface changes between landscape and
portrait aspect ratios. Weston's fallback panel is hidden so GNOME owns the
complete visible output, while the recovery compositor remains underneath.

Maliit and GNOME Shell provide the on-screen keyboard. Device-specific input
rules normalize finger, S Pen, navigation-key, volume-key, Power-key, and Active
button behavior.

## Hardware enablement

- Wi-Fi reuses the matching stock firmware extracted locally from the tablet's
  stock image and runs under NetworkManager.
- Bluetooth uses the WCN6850 UART. The kernel patches restore Samsung-disabled
  HCI socket support, Qualcomm initialization, and the board-specific RXD wake
  pulse required after firmware handoff. A single-instance userspace supervisor
  restarts the complete firmware-loader/BlueZ stack after a bounded delay if its
  owned launcher exits.
- Audio uses the stock DSP firmware and calibration with guarded speaker routing.
  The microphone uses a demand-driven ALSA-to-PipeWire bridge.
- Sensors use Samsung's DSP stack through a narrow downstream FastRPC adapter
  and Linux's standard sensor-proxy interface. Rotation is synchronized across
  three layers: a small Weston module changes the real DSI output transform,
  Xwayland switches between 1920×1200 and 1200×1920, and Mutter selects the
  matching dummy-monitor mode while remaining at transform zero. A
  session-local controller applies the SM-T630's calibrated absolute sensor
  map after a debounce, avoiding relative-rotation feedback.
- GPU experiments use Mesa Turnip/Zink through KGSL, with health checks and an
  automatic software-rendered fallback.
- Video playback has an exact-device-guarded, process-scoped adapter to the
  stock Qualcomm decoder. FFmpeg uses it for the touch-friendly Videos launcher;
  the opt-in GStreamer mode also translates Samsung's format, buffer-plane and
  end-of-stream conventions. Build the redistributable adapter on a Linux
  target (or with a suitable cross compiler in `CC`) using
  `tools/build_t630_video_adapter.sh`.
- Camera development runs the stock camera HAL in an isolated Android
  Binder/VNDK compatibility environment with stock assets mounted read-only.
  Native SensorService and the stock framework HIDL adapter satisfy the rear
  HAL's exposure-control dependency without running Java SystemServer. The
  sensors deliver I420 frames to a source-built NDK client; the front stream is
  published through an on-demand GStreamer/PipeWire bridge.
  Proprietary binaries are never part of this repository.

## Safety model

Destructive scripts contain exact model, kernel, block-device, partition-name,
size, charge-state, and hash checks. Those checks are a last line of defense,
not a substitute for understanding the operation. A new firmware revision must
be audited and assigned its own verified constants.

Runtime services avoid writing Android persist/calibration partitions. Required
firmware and calibration are copied or mounted read-only from verified stock
sources wherever possible.

The first-boot backend accepts a non-secret validated profile separately from
the password. The password is sent only to `chpasswd` over stdin. The owner
marker is written last, after account, group, hostname, locale, keyboard and
timezone setup complete, so a partial run cannot start the normal desktop as if
provisioning had succeeded.
