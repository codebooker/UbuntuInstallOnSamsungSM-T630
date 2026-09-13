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

Unlocking permanently trips Knox. Relocking while custom images are installed
can brick the device. Do not relock as part of this guide.

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

## Recovery

If the diagnostic boot fails, return to Download Mode and restore the exact
matching stock package. The local `stock/` extracts are reference/recovery
inputs, but a complete Samsung package may contain additional partitions needed
for a full restore. Reflashing stock does not reset the Knox warranty bit.

Never relock the bootloader until every custom image has been replaced with
known-matching stock firmware and the device has booted successfully.
