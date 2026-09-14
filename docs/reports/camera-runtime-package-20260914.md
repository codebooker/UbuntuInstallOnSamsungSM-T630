# Redistributable camera runtime package (2026-09-14)

## Result

`tools/build_camera_runtime_deb.py` produced
`t630-camera-runtime_0.1.0_arm64.deb` from tracked scripts plus five ARM64
helpers built from repository source. Two packages built with the same epoch
were byte-identical.

- size: 53,404 bytes
- SHA256: `fa29aab61a1c456c365e195cc3217ef192ac551888d8a9374cb3234fe83c7569`
- architecture: ARM64

The package moves the NDK capture client and Binder placeholder out of the
selected owner's private Android-data directory and into `/usr/local/libexec`.
It also owns the sensor-service launcher, property shim, rear color filter,
camera lifecycle controls, GNOME launchers, sudo rule, exact node creator, and
validation helper.

## Private boundary

The package contains no Samsung/Qualcomm library, firmware image, calibration,
camera state, Android partition image, or captured frame. The clean-root checker
validates all five helpers as ARM64 and explicitly rejects representative private
camera artifacts under `/home` and `/data`. The proprietary compatibility image
must still be reconstructed locally from the owner's exact T630XXSBDZE3 factory
archive.

## Physical acceptance

The package installed into the identity-clean Ubuntu rehearsal root with its
public dependencies, an empty package audit, and no leaked mounts. The same
package paths were then adopted on the live tablet. A first late-uptime attempt
found the stock camera module short one media subdevice after a high-order
allocation failure. A clean restart restored contiguous memory; the bounded
front-camera validator then delivered eight 720×480 I420 frames with measurable
contrast through PipeWire and completed exclusive camera teardown.

Removal from the disposable root deleted the camera files while leaving the
desktop, hardware, and stock packages installed. Reapplying the exact closure
restored camera-runtime 0.1.0 and release-base 0.1.5 with both audits clean.

The exact release closure is now thirteen components plus release-base 0.1.5,
fourteen files total. Broader lighting/application tests and automatic factory
archive reconstruction remain.
