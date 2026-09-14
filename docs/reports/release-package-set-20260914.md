# Exact-version base package set (2026-09-14)

## Result

`tools/build_release_meta_deb.py` now emits a deterministic dependency-only
package for the native Ubuntu base:

- name: `t630-release-base_0.1.3_arm64.deb`
- size: 12,356 bytes
- SHA256: `0fc7f51e94a5cef6befe9d0e5028011ef4a7fa507dbb1631d65f055c1677546e`

The package locks these eleven components to the tested package revisions:

- first-boot 0.1.1
- desktop runtime 0.1.1
- hardware runtime 0.1.2
- boot runtime 0.1.0
- PolicyKit runtime 0.1.0
- native userspace 0.1.0
- pd-mapper 0.1.0
- libssc 0.4.4-t6303
- hexagonrpcd 0.4.0-t6303
- iio-sensor-proxy 3.9-t6303
- private stock assets 1.0.1+dze3

Two local builds were byte-identical. Native tablet extraction parsed all eleven
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
and version of the metapackage and all eleven dependencies. Its package-only
mode validated the tablet's twelve-file cache after the PolicyKit addition.
