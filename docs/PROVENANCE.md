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
| Ubuntu `policykit-1-gnome` source | `0.105-7ubuntu5`; orig SHA256 `1784494963b8bf9a00eedc6cd3a2868fb123b8a5e516e66c5eda48df17ab9369`, Debian patch SHA256 `957ebefe04c896fc621ef8c578f6e77f04e72cd2092c6500b47e578ae91d1cf1` |
| elogind source | `v255.27`; archive SHA256 `1ef0dffaad77e8d8ded047895fc5e60b7ab5cf7137d356cebd821cc5a0d566c9` |
| Ubuntu GDM source | `46.2-1ubuntu1~24.04.9`; orig SHA256 `4ee345422a16537150cd842450cda52b2ca86984bc51ee20cdc025dcf4bd268b`, Debian patch SHA256 `0a4bfa56afc053f257f56a7918c679fe3edce1048817811de359f80ef0fff653` |
| Ubuntu Mutter diagnostic source | `46.2-1ubuntu0.24.04.16`; orig SHA256 `009baa77f8362612caa2e18c338a1b3c8aad3b5fe2964c2fef7824d321228983`, Debian patch SHA256 `688d078edc4c5c8afb682d56216534fff37aebcf740cf4df16fcfd55387ddbfc`, DSC SHA256 `6c1684cfc841c6f1abbd59d5aade2dc2ca9016e82ec423763160c7418419e166`. Lab-only build, not a default compositor; see the [pressure-path report](reports/pen-pressure-path-20260915.md) |
| Mozilla native Firefox APT signing key | fingerprint `35BA A0B3 3E9E B396 F59C A838 C0BA 5CE6 DC63 15A3`; downloaded key SHA256 `3ecc63922b7795eb23fdc449ff9396f9114cb3cf186d6f5b53ad4cc3ebfbb11f` |
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
