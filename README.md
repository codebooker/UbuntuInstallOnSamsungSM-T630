# Ubuntu on the Samsung Galaxy Tab Active4 Pro (SM-T630)

Experimental native Ubuntu 24.04 bring-up for the **Wi-Fi Samsung Galaxy Tab
Active4 Pro, model SM-T630** (`gtact4prowifi`, Snapdragon 778G / SM7325).

This project boots Ubuntu directly on the tablet; it is not Termux, a chroot
inside Android, or a remote desktop. The first development tablet now boots a
full-screen GNOME desktop from internal storage.

> [!CAUTION]
> This is a development port, not a finished installer. Unlocking the
> bootloader wipes the tablet; booting custom software can permanently trip the
> Samsung Knox warranty state. A wrong image or partition target can make the
> tablet unbootable. Do not use files for an SM-T636, SM-T638, Tab S9, or any
> other model.

## Current status

| Component | Status |
| --- | --- |
| Native boot / internal Ubuntu root | Working on the test SM-T630 |
| 1920×1200 GNOME desktop | Working |
| Finger touch and S Pen | Working |
| Wi-Fi and key-only SSH | Working |
| Speakers, microphone, volume keys | Working |
| Bluetooth | Working with the included kernel patches |
| Power, Home, Back, Recents, red Active key | Working |
| Password lock and on-screen keyboard | Working |
| Charging and manual shallow suspend/wake | Working |
| Accelerometer, light, proximity, magnetometer | Working |
| GPU rendering | Experimental; software fallback retained |
| Stock hardware video decoding | Working for tested FFmpeg and GStreamer H.264/VP9 playback |
| Browser video acceleration | WebKit hardware selection verified; safe launcher blocked by the stock kernel's missing user-namespace support |
| Cameras | Front and rear launchers publish one camera at a time to GNOME Camera; rear image quality still needs a well-lit physical test |

The exact evidence and remaining limitations are in [STATUS.md](docs/STATUS.md).

## Supported baseline

The only validated baseline is:

- Model: `SM-T630`
- Device: `gtact4prowifi`
- Stock build used for development: `T630XXSBDZE3`
- Boot image format: Android boot header v3, gzip ramdisk
- Stock kernel baseline: `5.4.274-qgki-31225846-abT630XXSBDZE3`

The builders intentionally verify this baseline and refuse unexpected device,
partition, size, and kernel values. Supporting another firmware revision should
be treated as a porting task, not as a reason to remove those checks.

## Start here

1. Read the [installation and recovery guide](docs/INSTALL.md) completely.
2. Read the [architecture](docs/ARCHITECTURE.md) to understand what is stock,
   rebuilt, and Ubuntu-native.
3. Check [STATUS.md](docs/STATUS.md) before relying on a hardware feature.
4. Read the current [camera bring-up notes](docs/CAMERA.md) for that experimental stack.
5. Use the chronological [bring-up reports](docs/reports/) for measurements,
   regressions, and recovery details.

At present the repository can reproduce the conservative diagnostic boot image
from matching stock firmware. Packaging the tested persistent Ubuntu filesystem
into a safe public installer is still on the roadmap. Do not improvise the
one-time userdata installation from the lab scripts unless you can recover the
tablet independently.

## Repository layout

- `initramfs/` — first, RAM-only diagnostic boot
- `persistent/` — prototype initramfs for the internal Ubuntu root
- `tools/` — image builders, extraction utilities, probes, and regression tests
- `ubuntu/` — device-specific desktop, input, audio, power, sensor, and service code
- `patches/` — downstream-kernel changes, primarily Bluetooth and sensor support
- `camera/` — source-only camera compatibility experiments
- `docs/reports/` — dated evidence from the physical SM-T630

Stock Samsung images, firmware, calibration, Android proprietary binaries,
credentials, and generated boot/rootfs images are intentionally not included.

## Inspiration and upstream work

This port was inspired by
[ubuntu-galaxy-tab-s9-ultra](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra).
That project supplied useful design ideas, but its images, kernel, device tree,
partition layout, and flashing scripts are **not compatible** with the SM-T630.

See [PROVENANCE.md](docs/PROVENANCE.md) for the exact upstream revisions used.

## Contributing

Hardware reports and narrowly scoped fixes are welcome. Please include the
exact model, firmware build, kernel string, and whether the observation was
made after a cold boot. Never post device credentials, Wi-Fi secrets, serial
numbers, calibration blobs, or redistributed Samsung firmware.

## License

Original project userspace code is licensed under AGPL-3.0. Kernel patches and
third-party material retain their upstream licenses; see
[LICENSES.md](LICENSES.md).
