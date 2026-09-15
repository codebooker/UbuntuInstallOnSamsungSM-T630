# Source-only hardware runtime package (2026-09-14)

## Result

The redistributable hardware orchestration is now built by
`tools/build_hardware_runtime_deb.py` as a deterministic Debian package:

- name: `t630-hardware-runtime_0.1.2_all.deb`
- size: 31,524 bytes
- SHA256: `68831e1ac25b5ca1074c99c812c47c5969225865c3bbd2c71f6c770fb8e4094a`

Two builds with `SOURCE_DATE_EPOCH=1700000000` were byte-identical. Native
arm64 `dpkg-deb` parsed and extracted the result on the tablet. The payload
contains only UTF-8 scripts and policy plus the repository license. It contains
no home directory, `/opt/t630` development tree, firmware, calibration blob,
compiled library, executable binary, owner state, credential, or device
identity.

## Included orchestration

The package contains the tracked NetworkManager policy, sensor permission rule,
microphone bridge, Qualcomm Bluetooth helper, and startup/supervision scripts
for audio, Bluetooth, sensors, and IPA. It also contains the speaker and
microphone routing helpers, audio cleanup and device-permission helpers, and the
audio/video firmware staging scripts.

Version 0.1.2 also owns `/etc/t630-install-id` with the exact
`SM-T630-T630XXSBDZE3-Ubuntu-v1` value already enforced by hardware launchers.
This closes the previous fresh-root gap where the live system had the marker
but no release package would install it.

Sensor startup also has an explicit first-boot mode that skips only the normal
audio-readiness ordering wait. This lets the root-only installer rotation relay
bring up the accelerometer before an owner or owner audio session exists; the
ordinary post-account sensor path retains the established audio ordering.

The two WirePlumber policies are stored below
`/usr/local/share/t630/owner-config`. Desktop runtime 0.1.1 copies those fixed
files atomically into the installer-selected owner's `XDG_CONFIG_HOME`. This
keeps the package owner-neutral and avoids a baked-in user name, UID, GID, or
home path. A live migration on the development tablet produced byte-identical
owner copies while retaining the enabled Tablet Controls extension.

## Live health after migration

After deploying the updated owner helper and source policies to the development
tablet, IPA reported online, Wi-Fi was up, Bluetooth was powered, SensorProxy
reported an accelerometer, PipeWire retained `t630_speakers` and
`t630_microphone` as its defaults, the battery reported full, and the current
boot contained no tracked fault markers.

## Remaining package boundary

Version 0.1.2 depends on desktop runtime 0.1.1, NetworkManager, and its
`wpasupplicant` Wi-Fi backend. The backend is an explicit dependency because
release roots deliberately omit recommended packages. It also recommends the reproducible
`libssc`, `hexagonrpcd`, and `iio-sensor-proxy` t6303 builds plus the local-only
`t630-stock-assets` package. It deliberately excludes
`pd-mapper`, patched GDM/elogind components, camera and video adapters,
Bluetooth firmware, speaker calibration, Qualcomm firmware, Android libraries,
SSH identity, and Wi-Fi credentials. Those components need other
architecture-specific builds or locally generated packages from the owner's
matching Samsung firmware before a generic release root can be assembled.
