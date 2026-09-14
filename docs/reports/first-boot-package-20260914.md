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

The real backend was later executed inside the fresh Ubuntu 24.04.5 ARM64
rehearsal root using a non-personal sample profile and password. It created the
UID/GID 1000 owner, marked the password active, selected only existing device
groups, wrote hostname/locale/keyboard/time-zone state, and passed the packaged
desktop autostart check. A UTS namespace kept the rehearsal hostname change from
touching the live tablet. A second backend run was refused, and the identity
audit then reported exactly the expected owner/profile/home/account state.

This closes package and backend execution for the first-boot component. A
physical clean-boot walkthrough through all touch UI pages still remains.
