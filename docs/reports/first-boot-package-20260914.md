# Reproducible first-boot package (2026-09-14)

The account-neutral setup flow is now assembled as a deterministic Debian
package by `tools/build_first_boot_deb.py`. With
`SOURCE_DATE_EPOCH=1700000000`, two independent builds were byte-identical.

The current tested artifact is:

- name: `t630-first-boot_0.1.1_all.deb`
- size: 20,904 bytes
- SHA256: `a18e0a100b006b8f9afd82c3ff28501a27c37ee1e0680c80efca1699f9e5d9b2`

The package was copied to the physical arm64 tablet and parsed and extracted
with Ubuntu's native `dpkg-deb`. Its executable modes, license, account helper,
backend, touch UI, Wi-Fi launcher, profile applier, and non-secret example
profile were present. No owner marker was created and the package was not
installed over the live development files.

Version 0.1.1 adds an explicit `--preview` mode for visual acceptance on an
already provisioned tablet. The mode is visibly labelled, disables its Wi-Fi
launcher, exits before the account backend can be invoked, and clears the two
password fields before closing. The real no-argument setup path and its owner
guard are unchanged.

The preview was rendered through the physical tablet's 1920×1200 scanout. The
Welcome page filled the display, text and controls were legible at touch size,
the selector did not clip, and navigation used the conventional Back-left /
Next-right order after correcting the first inspected layout. The live owner
marker remained present and unchanged, proving this was not mistaken for real
first boot. The preview also survived a full automatic suspend/RTC-wake cycle.

Two independent 0.1.1 builds with `SOURCE_DATE_EPOCH=1700000000` were
byte-identical. The final artifact was parsed and extracted again by native
arm64 `dpkg-deb`; its executable mode and preview flag were present and the
extracted tree contained no owner marker.

This closes packaging for the first-boot component itself. It does not close
the release-image gate: the rest of the device runtime, compiled helpers, and
matching stock-derived firmware still need reproducible packaging, followed by
a fresh-root installation test and visual first-boot acceptance.
