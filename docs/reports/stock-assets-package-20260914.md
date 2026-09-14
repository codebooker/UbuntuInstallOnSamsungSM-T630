# Private DZE3 stock-assets package (2026-09-14)

## Result

`tools/build_stock_assets_deb.py` now converts a prepared exact-stock source
tree into a deterministic, local-only Debian package:

- name: `t630-stock-assets_1.0.1+dze3_arm64.deb`
- size: 37,666,460 bytes
- SHA256: `934f3c361fedc806eef90b4b92a6f93c906492b6b29339cb4e2cf85c0c7b461e`
- selected static entries: 592

Two builds on the tablet with `SOURCE_DATE_EPOCH=1700000000` were byte-for-byte
identical. The output remained on the tablet and was not copied into the source
repository because it contains proprietary Samsung and Qualcomm material.

## Included boundary

The package selects the static DZE3 files used by native Ubuntu boot and device
services: stock kernel modules, Wi-Fi/touch/BT firmware, audio firmware and
configuration, IPA and video firmware, camera coprocessor firmware, SSC DSP
files, and read-only sensor configuration. The runtime SSC registry and socinfo
directories are created empty so the sensor daemon can initialize them without
modifying Android persist.

Fourteen critical files across Wi-Fi, touch, audio, Bluetooth, IPA, video,
sensors, and kernel modules must match hard-coded DZE3 SHA256 values before any
package is written. The package then records the size, mode, type, destination,
and SHA256 of every selected regular file in its own source manifest. Absolute
or escaping symlinks are rejected.

## Identity and mutable-state exclusions

The selected source map contains no home directory, account marker, SSH key,
NetworkManager connection, machine identity, Android data, Bluetooth address,
EFS speaker calibration, or existing SSC registry/socinfo state. Two vendor
firmware symlinks that point into mutable Android data are explicitly omitted:
the persistent Wi-Fi MAC link and the WLAN OTA-update link. Wi-Fi already works
without copying either link.

Native extraction confirmed the private package metadata and DZE3 dependency,
an empty SSC registry and socinfo tree, absence of both excluded symlinks, and a
matching packaged Wi-Fi-module hash. The package depends on
`t630-hardware-runtime (= 0.1.2)` and is labeled in the Debian `non-free/admin`
section.

## Remaining installer boundary

The current development tablet already has validated static copies staged at
the source paths consumed by the builder. A release installer must instead
prepare that source tree directly from the owner's exact factory firmware and
read-only stock partitions, then run this builder locally. That archive-to-tree
step, creation of per-device identities at first boot, and fresh-root package
installation remain gates. The package itself must never be redistributed.
