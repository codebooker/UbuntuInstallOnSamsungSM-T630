# Installation and recovery guide

> [!WARNING]
> The daily-driver installer is not finished. This document currently covers
> the validated preparation and RAM-only diagnostic boot. The persistent-root
> scripts are published for review and continued development, not as a blind
> copy-and-paste installer.

## 1. Confirm the exact tablet

Start from stock Android, enable Developer options and USB debugging, authorize
your computer, then record:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.product.device
adb shell getprop ro.build.version.incremental
adb shell getprop ro.boot.bootloader
adb shell uname -r
```

The validated device reported `SM-T630`, `gtact4prowifi`, and build/bootloader
`T630XXSBDZE3`. Stop if the model is not exactly SM-T630. A different firmware
revision needs its hashes and boot metadata audited before use.

## 2. Prepare for recovery first

Before unlocking or flashing:

1. Download the complete, matching Samsung factory firmware for your tablet's
   region/build and keep an untouched copy.
2. Verify that Download Mode is reachable and that your computer can detect the
   tablet.
3. Have a known method to flash the full stock package. Odin on Windows is the
   usual Samsung recovery route; Heimdall is used by this project for its narrow
   development flashes.
4. Charge the tablet above 50% and use a reliable data cable.
5. Copy off anything you care about. Bootloader unlock and the eventual Ubuntu
   installation erase userdata.

Unlocking wiped the test tablet but did not by itself change its Knox warranty
bit. Booting custom software later changed that bit permanently. Relocking while
custom images are installed can brick the device. Do not relock as part of this
guide.

## 3. Unlock the bootloader

On stock Android, enable **OEM unlocking** in Developer options. Power off, hold
both volume buttons while connecting USB, and enter Download Mode. Follow the
on-screen long-press Volume Up prompt for Device Unlock Mode, then confirm the
wipe. Let Android boot and complete enough setup to reconnect to Wi-Fi and
confirm OEM unlocking remains allowed.

Samsung Knox Guard may report `Prenormal` and temporarily hide OEM unlocking.
Do not attempt random partition writes to bypass it. Complete stock setup,
connect to the network, ensure the clock is correct, and return only when the
official unlock prompt is available.

## 4. Get the build tools

On macOS, install Python 3, CMake, pkg-config, libusb, LZ4, Zstandard, and
Android platform tools. On Debian/Ubuntu, install their normal distribution
equivalents.

Fetch the pinned AOSP and Heimdall sources used by the builders:

```sh
./tools/fetch_sources.sh
```

Fetch and verify the exact Ubuntu arm64 BusyBox package used in the diagnostic
initramfs:

```sh
./tools/fetch_busybox.sh
```

Build Heimdall from `tools/heimdall-source` according to its upstream README.
The physical test used Heimdall commit
`8f3044db985fd9710038f04886b51240ddbb2834`.

The native kernel build is separate from the deferred Android-container build.
On a case-sensitive Linux filesystem, use a fresh extraction of Samsung's
matching source and an empty output directory:

```sh
./tools/build_native_kernel.sh /absolute/path/to/fresh-source /absolute/path/to/empty-output
```

The builder authenticates the baseline source files, applies only the audited
native hardware/compiler fixes, rejects the namespace options that would change
the stock module ABI, and builds the Image plus matching modules. A successful
compile is not permission to flash an image; boot packing and the guarded write
checks below still apply.

## 5. Extract your matching stock images

The repository never supplies Samsung firmware. Point the extractor at your own
factory ZIP:

```sh
python3 tools/extract_stock.py /absolute/path/to/SM-T630-factory.zip
```

It extracts only boot, vendor_boot, recovery, DTBO, and vbmeta inputs into the
ignored `stock/` directory and writes a local hash manifest. Keep these files for
recovery; do not commit them.

## 6. Build the RAM-only diagnostic image

The current builder is pinned to the exact tested DZE3 boot metadata and Ubuntu
BusyBox package. After completing the two fetch steps and stock extraction, run:

```sh
python3 tools/build_boot_test.py
```

Expected local outputs are ignored by Git and appear under `output/`:

- `boot-test.img` — stock kernel plus diagnostic initramfs
- `vbmeta-test.img` — flags=2 empty vbmeta used by the test device

The builder reopens the image, verifies the boot metadata, compares the kernel
byte-for-byte with stock, validates the ramdisk, checks the partition size, and
runs AVB verification. A successful build does **not** make an unreviewed device
safe to flash.

## 7. Flash only after reviewing every value

The first physical test flashed only `BOOT` and `VBMETA`, without repartitioning
or a PIT upload. Heimdall reported both transfers successful. The tested command
shape was:

```sh
heimdall flash --BOOT output/boot-test.img --VBMETA output/vbmeta-test.img
```

Use `--resume` only if you intentionally began and retained the same Heimdall
Download Mode session. Never add `--repartition`, `--pit`, or a size-check bypass
for this step.

After reboot, the test image presents Samsung's unofficial-software warning and
then runs Linux behind it. There is no framebuffer console. Connect the USB data
cable and look for the serial device named **SM-T630 RAM-only diagnostic
console**. The root filesystem is RAM-only and does not mount internal storage.

## 8. Stop at the diagnostic milestone

Confirm the serial shell, kernel identity, `/init` as PID 1, and that no internal
filesystem is mounted. The exact expected evidence is documented in
`docs/reports/first-flash-result.md` and
`docs/reports/ubuntu-ram-milestone.md`.

The persistent Ubuntu root process currently depends on a development snapshot
that has not yet been converted into a public, reproducible release artifact.
Until that packaging work is complete, use the persistent scripts as auditable
source and do not run the one-time formatter from an abbreviated guide.

## Release-image and first-boot gates

The current tablet is a development system and must not be cloned into a public
image. A release filesystem must be assembled from generic Ubuntu packages,
have no human account, and pass:

```sh
python3 tools/audit_release_root.py /absolute/path/to/candidate-root
```

The audit is read-only and reports categories only. It refuses an initialized
machine ID, SSH host keys, Wi-Fi or Netplan state, home contents, human accounts,
random seed, or an existing SM-T630 owner/setup marker.

On a clean image, `t630-desktop-autostart` launches the touch-first setup wizard
before GNOME. Its pages are Language, Accessibility, Keyboard, Network,
Account, Time Zone, Privacy, and Finish. The backend validates a non-secret JSON
profile such as `docs/examples/first-boot-profile.json`; the UI passes the
password separately over stdin. It creates the human account and the narrow
`t630-owner` group, then writes `/etc/t630/owner` last. Device services resolve
the selected account through the local password database and do not assume
`tablet`, UID 1000, a fixed GID, or a fixed home path.

These components are implemented and tested, but the generic Ubuntu root image
builder and complete end-to-end wipe/install/recovery rehearsal remain release
gates. Do not redistribute the development tablet's filesystem.

The account-neutral portion is also built as a deterministic Debian package:

```sh
SOURCE_DATE_EPOCH=1700000000 python3 tools/build_first_boot_deb.py
```

This creates `output/t630-first-boot_0.1.1_all.deb`. It contains only tracked
setup code and the non-secret example profile; it does not contain an owner
marker, user account, password, machine identity, SSH key, or network profile.
Building the package is not yet equivalent to building the complete release
root—the remaining device runtime, compiled helpers, and matching stock-derived
firmware still need their own reproducible packages.

On an already provisioned development tablet, the UI can be rendered without
changing any account or system setting:

```sh
/usr/local/libexec/t630-first-boot --preview
```

Preview mode disables the Wi-Fi launcher, never invokes the account backend,
labels itself visibly, clears its password fields on exit, and closes without
writing an owner marker. The normal no-argument path remains the real one-time
setup flow and still refuses to run after an owner exists.

## Recovery

If the diagnostic boot fails, return to Download Mode and restore the exact
matching stock package. The local `stock/` extracts are reference/recovery
inputs, but a complete Samsung package may contain additional partitions needed
for a full restore. Reflashing stock does not reset the Knox warranty bit.

Never relock the bootloader until every custom image has been replaced with
known-matching stock firmware and the device has booted successfully.
