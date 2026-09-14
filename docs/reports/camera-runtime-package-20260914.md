# Redistributable camera runtime package (2026-09-14)

## Result

`tools/build_camera_runtime_deb.py` produced
`t630-camera-runtime_0.1.1_arm64.deb` from tracked scripts plus five ARM64
helpers built from repository source. Two packages built with the same epoch
were byte-identical.

- size: 53,520 bytes
- SHA256: `657d66ffda8db9958d0e87511edd30b9641367377bcea1c64af75acac7adc137`
- architecture: ARM64

The package moves the NDK capture client and Binder placeholder out of the
selected owner's private Android-data directory and into `/usr/local/libexec`.
It also owns the sensor-service launcher, property shim, rear color filter,
camera lifecycle controls, GNOME launchers, sudo rule, exact node creator, and
validation helper.

Version 0.1.1 also replaces the per-user `stock-vendor-full.img` dependency
with the checksum-verified physical `vendor` extent reported by Android LP
metadata. The helper creates read-only `t630-stock-system` and
`t630-stock-vendor` device-mapper targets from `/dev/sda26`; it validates the
exact tables before mounting either F2FS filesystem.

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

A second physical run used the direct vendor mapping and delivered eight bright,
high-contrast frames (mean luma 112.69, standard deviation 97.27). `findmnt`
identified `/dev/mapper/t630-stock-vendor` as the read-only source and `losetup`
showed no reference to the old image. The guarded shutdown unmounted both stock
filesystems and removed both mapper targets; the next boot reported no
device-mapper devices before camera start.

Removal from the disposable root deleted the camera files while leaving the
desktop, hardware, and stock packages installed. Reapplying the exact closure
restored camera-runtime 0.1.1 and release-base 0.1.6 with both audits clean.

The exact release closure is now thirteen components plus release-base 0.1.6,
fourteen files total. Broader lighting/application tests and automatic factory
archive reconstruction remain.
