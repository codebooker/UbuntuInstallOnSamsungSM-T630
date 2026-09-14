# Exact-version base package set (2026-09-14)

## Result

`tools/build_release_meta_deb.py` now emits a deterministic dependency-only
package for the native Ubuntu base:

- name: `t630-release-base_0.1.7_arm64.deb`
- SHA256: `d2ad6b14f92b38c7aeba292e490c17a64228e66df8b920ee17165bd4d6e992b0`

The package locks these thirteen components to the tested package revisions:

- first-boot 0.1.1
- desktop runtime 0.1.1
- hardware runtime 0.1.2
- boot runtime 0.1.0
- PolicyKit runtime 0.1.0
- login runtime 0.1.0
- camera runtime 0.1.2
- native userspace 0.1.0
- pd-mapper 0.1.0
- libssc 0.4.4-t6303
- hexagonrpcd 0.4.0-t6303
- iio-sensor-proxy 3.9-t6303
- private stock assets 1.0.1+dze3

Two local builds were byte-identical. Native tablet extraction parsed all
thirteen exact dependencies and the embedded JSON package-set record. The package itself
contains no firmware, account, credential, or device state. The private stock
package remains local-only even though its exact required version is named.

This is dependency closure, not yet a release image. A fresh Ubuntu root still
needs to be assembled, audited, booted, provisioned through first boot, and
recovered back to stock before the metapackage can be called end-user ready.
The redistributable camera compatibility layer is now part of this base package.
Its Samsung/Qualcomm runtime image, calibration, and mutable data remain outside
the package set and must be reconstructed locally from exact stock firmware.

`tools/assemble_release_root.py` independently pins the SHA256, package name,
and version of the metapackage and all thirteen dependencies. Its package-only
mode validated the tablet's fourteen-file cache after the camera-runtime addition.
