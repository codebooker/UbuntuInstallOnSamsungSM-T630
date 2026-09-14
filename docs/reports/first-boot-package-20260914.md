# Reproducible first-boot package (2026-09-14)

The account-neutral setup flow is now assembled as a deterministic Debian
package by `tools/build_first_boot_deb.py`. With
`SOURCE_DATE_EPOCH=1700000000`, two independent builds were byte-identical.

The current tested artifact is:

- name: `t630-first-boot_0.1.1_all.deb`
- size: 21,108 bytes
- SHA256: `2325f6224262ea1c23576fcaa638f839f5dacf492396b82469dc05dc45afe39d`

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

The physical preview later exposed a first-run keyboard failure: GTK 3 chose
Weston's unsupported text-input-v3 path, and the development device retained a
stock-keyboard recovery setting. The wizard now selects the packaged
`t630-wayland` text-input-v1 bridge before GTK initializes and focuses the first
account field when that page opens. The host keyboard launcher independently
forces Maliit whenever no owner exists, so a stale recovery preference cannot
strand the mandatory account screen. The repaired preview launched with the
Maliit process active, and the owner physically confirmed that the keyboard
appeared and accepted touch input. The final flow no longer exposes that
bootstrap keyboard: desktop runtime starts an unprivileged, RAM-only GNOME
installer host and connects only the root-owned setup frontend to it. The owner
physically confirmed that the resulting wizard uses the same GNOME keyboard as
the finished desktop. The host follows the physical Weston transform and
resizes both its Xwayland window and nested GNOME monitor between 1920x1200 and
1200x1920; the portrait layout and keyboard were accepted on the panel.
