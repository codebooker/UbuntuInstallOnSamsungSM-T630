# Reproducible first-boot package (2026-09-14)

The account-neutral setup flow is now assembled as a deterministic Debian
package by `tools/build_first_boot_deb.py`. With
`SOURCE_DATE_EPOCH=1700000000`, two independent builds were byte-identical.

The tested artifact was:

- name: `t630-first-boot_0.1.0_all.deb`
- size: 20,692 bytes
- SHA256: `f780e42bddf546e7bc859f2333051f3b0af965b4236899072366496d7958a30a`

The package was copied to the physical arm64 tablet and parsed and extracted
with Ubuntu's native `dpkg-deb`. Its executable modes, license, account helper,
backend, touch UI, Wi-Fi launcher, profile applier, and non-secret example
profile were present. No owner marker was created and the package was not
installed over the live development files.

This closes packaging for the first-boot component itself. It does not close
the release-image gate: the rest of the device runtime, compiled helpers, and
matching stock-derived firmware still need reproducible packaging, followed by
a fresh-root installation test and visual first-boot acceptance.
