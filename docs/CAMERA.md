# Camera bring-up

Camera support is an active compatibility experiment. It is not part of the
normal desktop yet, but the front camera has produced real 640x480 frames on
the physical SM-T630.

## What works

The exact stock `camera.ko` creates the two Qualcomm camera media graphs. The
matching Samsung camera provider and Android CameraService can run alongside
Ubuntu in a deliberately small Binder/VNDK environment. The source-only client
in `camera/t630-camera-capture.c` opens camera ID 1 (front, S5K4HA), configures a
YUV stream, receives capture callbacks, and writes the Y plane as a PGM image.

The compatibility stack disables CameraService's process-killing watchdog. In
a complete Android system the watchdog reports failures through system_server
and tombstoned. Neither exists here, and leaving it enabled can terminate the
hybrid camera stack during an ordinary HAL timeout.

The runtime mounts stock system/vendor/APEX content read-only and uses a
separate Ubuntu-owned `/data` directory. It does not mount Android calibration
or identity partitions writable.

## What does not work yet

- The front camera is not yet exposed as a normal PipeWire or Video4Linux
  camera, so GNOME applications cannot select it.
- The capture client currently exports only grayscale PGM snapshots, not a
  continuous color stream.
- Camera ID 0 (rear, S5K3L6) opens and starts its sensor, but the Samsung HAL
  rejects its EEPROM module data and reports CRC/module-version errors. The
  request then fails before delivering a usable buffer.
- The stack still depends on proprietary binaries extracted from the owner's
  exact `T630XXSBDZE3` stock firmware. They cannot be distributed here.

## Source components

- `camera/t630-camera-mounts.sh` validates the exact device baseline and builds
  the read-only compatibility mount layout.
- `camera/t630-camera-stack.sh` starts the minimum Binder, allocator, provider,
  and CameraService processes and disables the incompatible watchdog.
- `camera/t630-binder-placeholder.c` supplies the small nullable display-event
  service response CameraService expects while constructing its BufferQueue.
- `camera/t630-camera-capture.c` is the Android NDK capture probe.
- `ubuntu/t630-android-property-seed.c` supplies the small set of Android
  properties and permission stubs needed outside Android.
- `ubuntu/t630-android-log-capture.py` records Android binary-log datagrams for
  diagnosis without running the full Android logging daemon.

## Safety and redistribution

Do not commit extracted `cameraserver`, camera HAL libraries, firmware,
calibration, raw logs, or captured images. The repository intentionally carries
only the independently written compatibility source and the instructions for
reconstructing a runtime from the user's matching stock package.

The next milestone is a continuous front-camera bridge that ordinary Ubuntu
camera applications can discover. Rear-camera work remains separate because
its failure is currently at module-calibration validation, not at the Ubuntu
frame handoff that was solved for the front camera.
