# Reproducible pd-mapper package (2026-09-14)

## Result

The audio DSP protection-domain service now has a pinned native build and
package path:

- name: `t630-pd-mapper_0.1.0_arm64.deb`
- size: 12,752 bytes
- SHA256: `9236ef5c8a6393d957895a3b153636cf97b1fec682701f4639292560a5365d55`
- upstream revision: `5ecd2fe926aca7abfe40724177f63b942cff3947`
- source archive SHA256: `08972b8813d08da5e20d27e57c5989398a0b750be92cd4398b5b21190c6ccdd0`

`tools/build_pd_mapper_deb.sh` downloads and verifies that exact source archive,
uses a fixed source-path map and linker build-id mode, applies the tracked
explicit-map-directory compatibility patch, and packages the result without
installing it. Two clean Ubuntu ARM64 builds were byte-identical.

Native extraction reported an AArch64 position-independent executable. The
physical clean-root boot caught an incorrect `libqrtr-glib0` package dependency:
the binary actually links `libqrtr.so.1`, supplied by Ubuntu's `libqrtr1`.
The corrected builder uses `libqrtr-dev`, declares `libqrtr1`, and the generic
root provisioner installs that exact runtime. All dynamic dependencies then
resolve to the expected libc, libqrtr, and liblzma libraries. The package
contains no home or device state. It was added to
the tablet's release-package cache but was deliberately not installed over the
known-working live daemon. The upstream source emits several compiler warnings;
none was introduced or suppressed by this packaging build.
