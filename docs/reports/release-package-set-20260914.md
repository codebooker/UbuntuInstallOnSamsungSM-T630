# Exact-version base package set (2026-09-14)

## Result

`tools/build_release_meta_deb.py` now emits a deterministic dependency-only
package for the native Ubuntu base:

- name: `t630-release-base_0.1.1_arm64.deb`
- size: 12,332 bytes
- SHA256: `428107c2bd29ca77537f1e4b55db9c9b762c7b9406a6ae8cd5c194928bf89dc9`

The package locks these nine components to the tested package revisions:

- first-boot 0.1.1
- desktop runtime 0.1.1
- hardware runtime 0.1.2
- native userspace 0.1.0
- pd-mapper 0.1.0
- libssc 0.4.4-t6303
- hexagonrpcd 0.4.0-t6303
- iio-sensor-proxy 3.9-t6303
- private stock assets 1.0.1+dze3

Two local builds were byte-identical. Native tablet extraction parsed all nine
exact dependencies and the embedded JSON package-set record. The package itself
contains no firmware, account, credential, or device state. The private stock
package remains local-only even though its exact required version is named.

This is dependency closure, not yet a release image. A fresh Ubuntu root still
needs to be assembled, audited, booted, provisioned through first boot, and
recovered back to stock before the metapackage can be called end-user ready.
The Android camera compatibility environment is deliberately not part of this
base package while its owner-neutral and redistributable boundaries remain
unfinished.

`tools/assemble_release_root.py` independently pins the SHA256, package name,
and version of the metapackage and all nine dependencies. Its package-only mode
validated the tablet's ten-file cache after the device-marker version advance.
