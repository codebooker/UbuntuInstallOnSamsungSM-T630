# Camera bring-up

Camera support is an active compatibility experiment. The front camera is now
available to GNOME Camera as a standard PipeWire video source on the physical
SM-T630. The rear camera also delivers frames through the native capture probe;
desktop switching and final image-quality validation remain to do.

## What works

The exact stock `camera.ko` creates the two Qualcomm camera media graphs. The
matching Samsung camera provider and Android CameraService can run alongside
Ubuntu in a deliberately small Binder/VNDK environment. The source-only client
in `camera/t630-camera-capture.c` opens camera ID 1 (front, S5K4HA), configures a
YUV stream, and exports either a one-frame grayscale PGM or a continuous I420
stream. The I420 stream feeds GStreamer, which publishes
`SM-T630_Front_Camera` to PipeWire. GNOME Camera was verified as an independent
consumer with an active PipeWire link and a captured PNG.

The compatibility stack disables CameraService's process-killing watchdog. In
a complete Android system the watchdog reports failures through system_server
and tombstoned. Neither exists here, and leaving it enabled can terminate the
hybrid camera stack during an ordinary HAL timeout.

The runtime mounts stock system/vendor/APEX content read-only and uses a
separate Ubuntu-owned `/data` directory. It does not mount Android calibration
or identity partitions writable.

The rebooted prototype completed a 300-frame PipeWire-to-VP8/WebM recording.
Opening and closing the GNOME Camera launcher repeatedly also starts and
releases the sensor without leaving its PipeWire source behind.

Camera ID 0 (rear, S5K3L6) now completes capture requests. The stock HAL needs
`ro.boot.revision=5` to select the matching DV2 board profile. Its AEC then asks
for `android.frameworks.sensorservice@1.0::ISensorManager/default`; without
Android SystemServer that lookup blocked forever, starved the sensor request
queue, and eventually tripped the camera watchdog. The compatibility stack now
starts native SensorService and a small source-built launcher that registers
Samsung's stock HIDL adapter. A clean automatic-stack test captured ten rear
frames followed by ten front frames, and a separate rear burst delivered 60
frames at 640x480/30 fps without killing the stack.

## What does not work yet

- Camera ID 0 is not yet published to PipeWire. The provider accepts only one
  active camera client, so desktop switching must stop the front stream before
  starting the rear one.
- The first recovered rear frame sequence was almost completely dark. CSI,
  CSID and IFE interrupts plus request completion were all healthy, but a
  well-lit physical target still needs to be captured before claiming image
  quality. Several rear EEPROM sections report the same stock-kernel CRC
  failures seen earlier.
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
- `camera/t630-sensorservice-hidl.cpp` registers the stock framework HIDL
  sensor adapter without starting Android's Java SystemServer.
- `ubuntu/t630-android-property-seed.c` supplies the small set of Android
  properties and permission stubs needed outside Android.
- `ubuntu/t630-android-log-capture.py` records Android binary-log datagrams for
  diagnosis without running the full Android logging daemon.
- `ubuntu/t630-camera-bridge` converts the NDK client's I420 stream into a
  standard PipeWire `Video/Source`.
- `ubuntu/t630-camera-control`, `t630-camera-app`, and the desktop file
  provide an on-demand lifecycle: the camera powers up when Camera opens and is
  released when the app exits.

## Building the sensor-service bridge

Install an Android NDK, set `ANDROID_NDK_ROOT`, then run:

```sh
tools/build_camera_sensor_bridge.sh
```

This creates an AArch64 property/permission shim and the HIDL adapter launcher
under `build/camera/`. The current launcher resolves private C++ symbols from
the stock libraries at runtime and is intentionally tied to the tested
`T630XXSBDZE3` image. Do not reuse it with another firmware build until its
symbols and behavior have been revalidated.

## Safety and redistribution

Do not commit extracted `cameraserver`, camera HAL libraries, firmware,
calibration, raw logs, or captured images. The repository intentionally carries
only the independently written compatibility source and the instructions for
reconstructing a runtime from the user's matching stock package.

The remaining camera work is rear image-quality validation, safe front/rear
desktop switching, physical orientation checking, and wider application
compatibility testing. Permission stubs are process-scoped to this isolated
compatibility runtime; they are not loaded into GNOME or ordinary Ubuntu
applications.
