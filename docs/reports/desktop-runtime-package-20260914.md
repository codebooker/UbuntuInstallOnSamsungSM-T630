# Account-neutral desktop runtime package (2026-09-14)

## Result

The architecture-independent Ubuntu integration is now built by
`tools/build_desktop_runtime_deb.py` as a deterministic Debian package:

- name: `t630-desktop-runtime_0.1.1_all.deb`
- size: 43,976 bytes
- SHA256: `0fc15a7e93d795644c6e755af8b1eb612b5b484ab19a33af7a442ca9f75dd770`
- regular files: 34

Two builds with `SOURCE_DATE_EPOCH=1700000000` were byte-identical. Native
arm64 `dpkg-deb` parsed and extracted the result on the tablet. Executable modes
for desktop startup, owner-asset setup, and guarded suspend were present. The
tree contained no `/home`, owner marker, first-boot profile, credential, network
profile, machine identity, compiled helper, or proprietary firmware.

The package depends on exactly `t630-first-boot (= 0.1.1)`, the source-built
native compatibility package, and standard Ubuntu
desktop utilities. It contains tracked desktop startup and session launchers,
login glue, physical-input mapping, display controls, rotation, Power handling,
automatic shallow suspend, the extension source, and the narrow udev/polkit
rules used by those components.

The first-run launcher now hosts the setup frontend inside a disposable GNOME
Shell running as the locked `nobody` account with all state below `/run`. This
gives account creation the same GNOME on-screen keyboard as the finished
desktop without granting the temporary shell root access or writing an
installer account into the image. A paired root sensor relay and unprivileged
GNOME resize helper keep the setup window synchronized with landscape and
portrait panel modes. Maliit remains the direct-Weston recovery fallback.

## Installer-selected owner migration

The previous development system had Tablet Controls copied directly into
`/home/tablet`. A release image cannot carry that directory or assume UID 1000.
The new `t630-install-owner-assets` helper runs only as the account resolved by
`/etc/t630/owner`. It validates three fixed, regular system-owned source files,
hashes them, compiles the extension schema in a same-filesystem temporary
directory, replaces only `t630-tablet-tools@local`, and preserves every other
enabled extension.

The helper was deployed to the physical tablet. A legacy root-owned parent
directory from the original manual setup was identified and corrected at that
exact path; a clean owner profile creates the parent itself. The helper then
installed the assets, wrote source digest
`25669e72d37994339ce3fcb082053529d038dc3704deb8bc944211b6434883bf`,
and retained `['t630-tablet-tools@local']` in GNOME's enabled-extension list.
Version 0.1.1 extends the same owner helper to optional policy sources below
`/usr/local/share/t630/owner-config`. It validates the two fixed WirePlumber
files as regular non-symlinks and installs each through a same-directory
temporary file and atomic replacement beneath the owner's `XDG_CONFIG_HOME`.
Unrelated configuration is preserved and a missing optional source is harmless.
The updated package was built reproducibly and extracted natively on the tablet.

Four isolated tests cover unsafe extension and configuration symlink rejection,
atomic compilation while preserving another extension, owner-policy copying,
and the matching-digest no-recompile path.

## Remaining package boundary

This package is intentionally source-only and architecture-independent. A
complete release root still needs separately reproducible native compatibility
libraries and daemons, plus a local package generated from the owner's exact
matching Samsung firmware where redistribution is not permitted. The retained
recovery environment and full wipe/install/return-to-stock rehearsal also
remain release gates.
