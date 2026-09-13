# Camera bring-up

Camera support is an active compatibility experiment. The front camera is
available to GNOME Camera as a standard PipeWire video source on the physical
SM-T630. The separate Rear Camera launcher starts rear ID 0 with a guarded
manual exposure baseline and rear-only tone correction; physical confirmation
of the latest color profile remains.

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

The client uses Android's continuous-preview request template and explicitly
enables automatic exposure, white balance, and focus for the front camera. On
the same indoor target, this moved it from 10 ms at sensitivity 58 (mean luma
20.98) to 40 ms at sensitivity 156 (mean luma 107.54). The rear logical path is
different: its preview template returns zero-filled buffers, while its still
template returns real but severely underexposed pixels. Rear therefore retains
the still template, disables AE so Samsung cannot replace explicit sensor
fields, and requests 30 ms at sensitivity 800. The capture log reports one set
of resulting exposure metadata per run rather than every completed request.

`ubuntu/test-t630-camera-frame.py` provides a repeatable, privacy-preserving
physical check. Run it through `t630-gnome-run` with either `front` or `rear`.
It captures eight I420 frames into the tablet user's volatile runtime directory,
reports only aggregate luma statistics as JSON, then deletes the raw stream and
turns the camera off in a `finally` block. It never writes a photograph to the
Ubuntu filesystem.

The camera module no longer runs a global `mdev` cold scan. A narrowly scoped
helper creates only the exact kernel-advertised camera/media nodes and validates
their device numbers. The usual guarded desktop permission repair follows it.
This preserves normal-user access to FUSE, current ALSA nodes, DRM render,
KGSL/ION and the hardware codec nodes. Without this change, opening a camera
could leave already-running services functional while preventing later Files,
audio, graphics and video processes from opening their devices.

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

The Camera desktop override must live under the session's actual
`XDG_DATA_HOME`, which is
`/home/tablet/.local/share/t630-gnome-preview/applications`, and must be named
`org.gnome.Snapshot.desktop`. Installing it in the account's conventional
`.local/share/applications` directory does not override the stock launcher in
this isolated session. The rear entry is installed beside it as
`t630-rear-camera.desktop`.

Snapshot is a single-instance application. The launcher now detects an exact
existing `/usr/bin/snapshot` process and keeps the selected hardware bridge
alive until that process exits; previously a second invocation returned at
once and disabled the source behind the still-visible window. It also stores
Snapshot's standard `is-maximized` preference so the camera follows both tablet
orientations instead of opening at its phone-sized 800×640 default.

Logical camera ID 0 (rear, S5K3L6) now completes capture requests. The stock HAL needs
`ro.boot.revision=5` to select the matching DV2 board profile. Its AEC then asks
for `android.frameworks.sensorservice@1.0::ISensorManager/default`; without
Android SystemServer that lookup blocked forever, starved the sensor request
queue, and eventually tripped the camera watchdog. The compatibility stack now
starts native SensorService and a small source-built launcher that registers
Samsung's stock HIDL adapter. A clean automatic-stack test captured ten rear
frames followed by ten front frames, and a separate rear burst delivered 60
frames at 640x480/30 fps without killing the stack. Outside the full Android
framework, its preview template delivers zero-filled YUV while claiming
converged AE; the still template instead exposes the real low-valued image. A
manual 60 ms / ISO 1600 diagnostic request raised raw mean luma from 1.17 to
5.89. A scoped GStreamer gamma 2.5 stage recovered shadow detail. When a brighter
real scene made that profile visibly overexposed (published mean 206.37), the
sensor baseline was reduced to 30 ms / ISO 800. The corrected live source
measured mean luma 162.26 with 1.39% near-white pixels before color tuning, and
160.35 with no near-white pixels afterward. Camera IDs 2 and 3 produce bright frames, but physical
inspection confirms that ID 3 is another front-camera endpoint; neither can
substitute for rear ID 0.

Rear manual AE leaves Samsung's automatic white balance inactive. Result
metadata reports `awb_state=0` and gains `1.391,1.000,1.000,2.469`. The HAL
advertises every standard white-balance preset, but an incandescent-preset
trial entered an active session without delivering a frame. The bridge therefore
keeps the known-good AUTO request and passes only rear I420 through the small
source-built `t630-yuv-tune` filter. Its current 0.92× red and 1.25× blue gains
move the measured chroma away from yellow while leaving luma essentially
unchanged; final visual tuning is still in progress.

The provider allows one camera client at a time. `t630-camera-control` therefore
stops the current bridge before selecting `front` or `rear`; it never keeps both
sensors powered. Both source transitions and cleanup were verified through
PipeWire, and the Rear Camera desktop launcher opened GNOME Camera with the rear
source active.

Bridge teardown closes the downstream GStreamer consumer first. The capture
client ignores SIGPIPE, observes the closed pipe as a normal write failure, and
unwinds through `ACameraCaptureSession_close()` before the control helper uses a
bounded owned-process-group fallback. This matters because a rapid queued
front/rear transition reproduced a stock `camera.ko` panic in
`cdm_write_genirq`; nonblocking transition locks and a five-second hardware
quiesce now prevent stale switch requests from reaching that path. The volatile
validator reports success only after cleanup passes.

Closing Camera also stops the isolated Android camera stack and removes its
readiness marker. This releases the provider's observed idle CPU and roughly
124 MiB resident footprint instead of keeping the compatibility runtime alive
indefinitely. The already-loaded stock camera kernel module and read-only mounts
are deliberately left in place; live module removal is not attempted.

## Remaining limitations

- Rear ID 0 does not provide trustworthy automatic exposure or white balance
  outside Android. The current 30 ms / ISO 800 baseline, gamma 2.5 tone lift,
  and userspace color correction remain conservative fixed profiles rather than
  scene-aware 3A; wider lighting, noise, frame-rate, and color tests remain.
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
- `camera/t630-yuv-tune.c` is the bounded streaming I420 red/blue correction
  used only for the rear source.
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
- `ubuntu/t630-camera-nodes.py` creates only video0/1, v4l-subdev0–16 and
  media0/1 from their exact sysfs device numbers; it deliberately ignores the
  separately governed video32/33 codec nodes.

## Building the sensor-service bridge

Install Android NDK r27 or newer, set `ANDROID_NDK_ROOT`, then run:

```sh
tools/build_camera_sensor_bridge.sh
```

This creates the AArch64 property/permission shim, HIDL adapter launcher, and
NDK capture client under `build/camera/`. The capture client resolves the two
Binder thread-pool entry points dynamically because the Android runtime exports
them but the public NDK link stub does not. The compatibility code is
intentionally tied to the tested `T630XXSBDZE3` image. Do not reuse it with
another firmware build until its symbols and behavior have been revalidated.

## Safety and redistribution

Do not commit extracted `cameraserver`, camera HAL libraries, firmware,
calibration, raw logs, or captured images. The repository intentionally carries
only the independently written compatibility source and the instructions for
reconstructing a runtime from the user's matching stock package.

The remaining camera work is physical validation and tuning of the rear manual
profile, orientation checking, and wider application compatibility testing.
Permission stubs are process-scoped to this isolated compatibility runtime;
they are not loaded into GNOME or ordinary Ubuntu applications.

After the launcher/session-path repair, a front validation delivered eight
frames with mean luma 20.98. With preview-mode 3A enabled, a fresh front run
delivered eight frames with range 7–255, mean 107.54, and standard deviation
95.51; the HAL reported 40 ms exposure at sensitivity 156. The rear HAL also
responded by increasing to 41.7 ms at sensitivity 994, but that path's final
frame was entirely black. IDs 2 and 3 delivered bright frames; physical
inspection of ID 3 showed the front camera, so the rear bridge remains mapped
to ID 0. Switching ID 0 back to the still template recovered real pixels; an
authoritative 60 ms / ISO 1600 diagnostic request plus rear-only gamma 2.5
proved the path, but was too bright in the later physical scene. The deployed
30 ms / ISO 800 profile measured mean luma 160.35 with no near-white pixels
after userspace color tuning. Each validator removed its volatile raw stream.

Build the Ubuntu-native color filter on the tablet (or another AArch64 Ubuntu
host) with:

```sh
tools/build_camera_color_filter.sh
```
