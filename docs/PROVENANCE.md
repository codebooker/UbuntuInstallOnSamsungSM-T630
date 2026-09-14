# Source and artifact provenance

The repository contains source and patches only. It intentionally excludes
Samsung factory images, firmware, calibration data, proprietary Android camera
or media binaries, generated Ubuntu root filesystems, compiled kernels, and
boot images.

`tools/build_stock_assets_deb.py` creates a private package only from an
owner-supplied, prepared exact-DZE3 source tree. It checks a fixed set of
critical firmware, module, audio, sensor, touch, and Wi-Fi hashes and records a
SHA256 manifest for every selected file inside the local package. The generated
package is ignored by Git and is not redistributable. Per-device Wi-Fi and
Bluetooth identities, EFS calibration, mutable sensor state, accounts, and
network credentials are outside that package boundary.

Pinned development references:

| Dependency | Revision |
| --- | --- |
| AOSP `platform/system/tools/mkbootimg` | `d2bb0af5ba6d3198a3e99529c97eda1be0b5a093` |
| AOSP `platform/external/avb` | `c5066a96caa7bf4150c0a8cc8cc14ab81733fdc7` |
| Heimdall | `8f3044db985fd9710038f04886b51240ddbb2834` |
| linux-msm `pd-mapper` | `5ecd2fe926aca7abfe40724177f63b942cff3947` |
| S9 Ultra inspiration/reference | `bb55ceb87b61db7629c0820101ce7884ff8d987b` |
| Waydroid source reviewed for container/session integration | `5a51271131bfca8b7ee75ed067d09b26460f3a7b` |

Samsung publishes the SM-T630 kernel source through its Open Source Release
Center. Obtain the source matching your firmware there rather than copying a
different model's kernel.

The tested DZE3 release archive has SHA-256
`30bc36cdd0378685f39714030cc7ff7aa6d6538367d517844e158aa2e9eb9ab2`;
its embedded `Kernel.tar.gz` has SHA-256
`0b66a4a653e6ac164923a8cdbec83f66e1bcd71c51fab76fbd1155807be76db7`.
The kernel builder additionally verifies the individual baseline files touched
by this project's patches before it changes the source tree.

Kernel patch files remain subject to the license of the kernel source to which
they apply. Third-party projects retain their own licenses and are fetched into
ignored directories rather than vendored into this repository.
