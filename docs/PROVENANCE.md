# Source and artifact provenance

The repository contains source and patches only. It intentionally excludes
Samsung factory images, firmware, calibration data, proprietary Android camera
or media binaries, generated Ubuntu root filesystems, compiled kernels, and
boot images.

Pinned development references:

| Dependency | Revision |
| --- | --- |
| AOSP `platform/system/tools/mkbootimg` | `d2bb0af5ba6d3198a3e99529c97eda1be0b5a093` |
| AOSP `platform/external/avb` | `c5066a96caa7bf4150c0a8cc8cc14ab81733fdc7` |
| Heimdall | `8f3044db985fd9710038f04886b51240ddbb2834` |
| linux-msm `pd-mapper` | `5ecd2fe926aca7abfe40724177f63b942cff3947` |
| S9 Ultra inspiration/reference | `bb55ceb87b61db7629c0820101ce7884ff8d987b` |

Samsung publishes the SM-T630 kernel source through its Open Source Release
Center. Obtain the source matching your firmware there rather than copying a
different model's kernel.

Kernel patch files remain subject to the license of the kernel source to which
they apply. Third-party projects retain their own licenses and are fetched into
ignored directories rather than vendored into this repository.
