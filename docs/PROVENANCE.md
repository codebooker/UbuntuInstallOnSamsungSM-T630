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
| Ubuntu Xwayland proximity source inspection | `2:23.2.6-1ubuntu0.8`; orig SHA256 `1c9a366b4e7ccadba0f9bd313c59eae12d23bd72543b22a26eaf8b20835cfc6d`, Debian patch SHA256 `00c7667cf0109ee79c60b196d63db7ecc8baf45ed1d65263d85fc122bd699aba`, DSC SHA256 `99174d7e4d6c46375bd5b978c05f325644f7c1d02f08fb2588803798944330a2`. Source inspection only; no replacement binary installed |
| Waydroid source reviewed for container/session integration | `5a51271131bfca8b7ee75ed067d09b26460f3a7b` |
| Waydroid host packages used for physical acceptance | `waydroid` 1.6.2, `lxc` 1:5.0.3-2ubuntu7.2, `python3-gbinder` 1.3.1 from the Waydroid Noble repository / Ubuntu 24.04 dependencies |
| SM-T630 Waydroid integration package | `t630-waydroid-runtime` 0.1.7, reproducible package SHA256 `2ee6d4c414b9e811e6bdaef307dfc40714080bde9b0042c1454056d6fab065db` |
| SM-T630 desktop integration package | `t630-desktop-runtime` 0.1.12, reproducible package SHA256 `3898ecbb797a11e41fe1e231e65752805b1bba232ddaabd7e71d0a25adde54a4` |
| SM-T630 exact-version base metapackage | `t630-release-base` 0.1.21, reproducible package SHA256 `6845abca54bda669795acdd115ad19d6b1de3d5826c06b8b4b1fa22d96d53b0a` |
| Official Waydroid ARM64 VANILLA image acceptance artifacts | `system.img` SHA256 `e9d0a498105feb5e00895066dee90d738b3961ba334416f26498e357ee966b2e`; MAINLINE `vendor.img` SHA256 `b18a05747db565c134db48031caeec3ce4bd9e0ce8f88ef9c679f3ef9e24e39a` |
| Official Waydroid ARM64 GAPPS image acceptance artifacts | `lineage-20.0-20260403-GAPPS-waydroid_arm64-system.zip`, 1,326,285,880 bytes, SHA256 `c5e557605887664ab1da6c17ff0032317735a0425b8055ee9073fdbcd00899c2`; extracted `system.img` SHA256 `b21bb8508157fdd3fe0611d5770c9103403a4a0834f3713650ddcf25a6fb1578`; MAINLINE `vendor.img` SHA256 `b18a05747db565c134db48031caeec3ce4bd9e0ce8f88ef9c679f3ef9e24e39a` |
| F-Droid physical acceptance artifact | 1.23.2 (versionCode 1023052), canonical `F-Droid.apk` SHA256 `985f5181d48bb6bafd54083a048b391271e0ab28385881cc41294fb01a222762` |
| CodeLinaro Qualcomm WLAN `qcacld-3.0` (`LA.UM.9.14.r1-19400-LAHAINA.QSSI13.0`) | `4e15799e1f443577a9a102bc0c9564259e502b03` |
| CodeLinaro Qualcomm WLAN `qca-wifi-host-cmn` (same release) | `0904701ee8ae065bbc920c7d5a2a11c0c645ebaa` |
| CodeLinaro Qualcomm WLAN `fw-api` (same release) | `2b58351f875928929af63aa548fa0b84f3050587` |
| Ubuntu MyPaint isolated GIL-fix trial source | `2.0.1-10build2`; orig SHA256 `f3e437d7cdd5fd28ef6532e8ab6b4b05d842bcdd644f16a0162dad3d8e57bb16`, Debian patch SHA256 `47a93a2da9943973ba8487605693eba26526ae7591a93fe94a46ab12518bedc3`, DSC SHA256 `102e820aa04e7b6de5d2d60f0f6a981e3b51bcb0869dcbc086fab511a81b25cb`. Source/build only; not a replaced installed app |
| MyPaint upstream GIL fix | `356716e7bacfcbb1f3ab80171fea405fdd10b2b9`; official commit patch SHA256 `182fcc05df0b0452d3a9a93dab79e5c70bb4beb6464a12f551c6508d30b377a7`; applied without hunk offsets or fuzz to the isolated exact-version source |
| Private MyPaint GIL-fix lab artifacts | `_mypaintlib.cpython-312-aarch64-linux-gnu.so` SHA256 `969627187a15ae4f9128944b24f55a730ca95e2d914e2ece604676bb3d5482c4`, generated `mypaintlib.py` SHA256 `d154b514ccf4ef84becff8676bb73f47888b2533feb083078651f454d3046be7`. Built on the tablet original Ubuntu root with `python3 setup.py build_ext --inplace --parallel 2`; pinned only for private headless testing, not distributed or installed |

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
