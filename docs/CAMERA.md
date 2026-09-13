# Camera bring-up

Camera support is an active compatibility experiment. The front camera is now
available to GNOME Camera as a standard PipeWire video source on the physical
SM-T630. A separate Rear Camera launcher publishes the rear stream to the same
application; final rear image-quality validation remains to do.

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

`ubuntu/test-t630-camera-frame.py` provides a repeatable, privacy-preserving
physical check. Run it through `t630-gnome-run` with either `front` or `rear`.
It captures eight I420 frames into the tablet user's volatile runtime directory,
reports only aggregate luma statistics as JSON, then deletes the raw stream and
turns the camera off in a `finally` block. It never writes a photograph to the
Ubuntu filesystem.

The camera module's cold device scan is followed immediately by the same
guarded permission repair used during desktop startup. This preserves normal
user access to conventional `/dev` endpoints, current ALSA nodes, DRM render,
KGSL/ION and the hardware codec nodes. Without that repair, opening a camera
could leave already-running audio functional while preventing later audio,
graphics and video processes from opening their devices.

Android log capture is capped at 4 MiB in `/run`. A live stress test sent more
than 6 MiB of printable camera-log traffic; the file stayed below its cap, the
logger remained alive, and the front stream continued running. This prevents a
long or verbose camera session from exhausting the tablet's small `/run` tmpfs.

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

The provider allows one camera client at a time. `t630-camera-control` therefore
stops the current bridge before selecting `front` or `rear`; it never keeps both
sensors powered. Both source transitions and cleanup were verified through
PipeWire, and the Rear Camera desktop launcher opened GNOME Camera with the rear
source active.

Bridge teardown first requests a normal exit, then bounds an unresponsive
GStreamer/capture group and escalates only that still-validated owned process
group. The volatile validator reports success only after this cleanup passes,
preventing a delivered frame from hiding a stuck camera process.

Closing Camera also stops the isolated Android camera stack and removes its
readiness marker. This releases the provider's observed idle CPU and roughly
124 MiB resident footprint instead of keeping the compatibility runtime alive
indefinitely. The already-loaded stock camera kernel module and read-only mounts
are deliberately left in place; live module removal is not attempted.

## What does not work yet

- The first recovered rear frame sequence was almost completely dark. CSI,
  CSID and IFE interrupts plus request completion were all healthy, but a
  well-lit physical target still needs to be captured before claiming image
  quality. The accelerometer simultaneously reported the tablet lying flat and
  face-up, with the rear lens pointed into its supporting surface. Several rear
  EEPROM sections report the same stock-kernel CRC failures seen earlier.
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
- `ubuntu/t630-camera-bridge` converts the selected NDK I420 stream into a
  standard front or rear PipeWire `Video/Source`.
- `ubuntu/t630-camera-control`, `t630-camera-app`, and the two desktop files
  provide an exclusive, on-demand lifecycle: the selected camera powers up when
  its launcher opens and is released when the app exits.
- `ubuntu/test-t630-camera-frame.py` validates delivery and contrast without
  retaining a frame. On boot `4d826579-5c53-47e3-8edd-dc3d6ffd8d0b`, the front
  sensor delivered eight frames with luma range 0–38 and standard deviation
  7.49. The rear sensor delivered eight frames but remained nearly uniform
  (range 0–7, standard deviation 0.46) while its lens faced the support surface.

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

The remaining camera work is rear image-quality validation, physical
orientation checking, and wider application compatibility testing. Permission
stubs are process-scoped to this isolated compatibility runtime; they are not
loaded into GNOME or ordinary Ubuntu applications.
