# Reproducible pd-mapper package (2026-09-14)

## Result

The audio DSP protection-domain service now has a pinned native build and
package path:

- name: `t630-pd-mapper_0.1.0_arm64.deb`
- size: 12,346 bytes
- SHA256: `f0d06b0b6be7fe94f2c1b868e3a0c4856e89216768cbb2bbe43a8e0e381a6960`
- upstream revision: `5ecd2fe926aca7abfe40724177f63b942cff3947`
- source archive SHA256: `08972b8813d08da5e20d27e57c5989398a0b750be92cd4398b5b21190c6ccdd0`

`tools/build_pd_mapper_deb.sh` downloads and verifies that exact source archive,
uses a fixed source-path map and linker build-id mode, and packages the result
without installing it. Two clean builds on the tablet were byte-identical.

Native extraction reported an AArch64 position-independent executable. All
dynamic dependencies resolved to the expected libc, libqrtr, and liblzma
libraries, and the package contained no home or device state. It was added to
the tablet's release-package cache but was deliberately not installed over the
known-working live daemon. The upstream source emits several compiler warnings;
none was introduced or suppressed by this packaging build.
