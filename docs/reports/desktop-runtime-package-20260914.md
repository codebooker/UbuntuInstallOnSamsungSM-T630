# Account-neutral desktop runtime package (2026-09-14)

## Result

The architecture-independent Ubuntu integration is now built by
`tools/build_desktop_runtime_deb.py` as a deterministic Debian package:

- name: `t630-desktop-runtime_0.1.0_all.deb`
- size: 41,460 bytes
- SHA256: `7b044524dd93f108f07b005c0eb4edc8cb18fe22003a8f1371da32cdf392b28a`
- regular files: 31

Two builds with `SOURCE_DATE_EPOCH=1700000000` were byte-identical. Native
arm64 `dpkg-deb` parsed and extracted the result on the tablet. Executable modes
for desktop startup, owner-asset setup, and guarded suspend were present. The
tree contained no `/home`, owner marker, first-boot profile, credential, network
profile, machine identity, compiled helper, or proprietary firmware.

The package depends on exactly `t630-first-boot (= 0.1.1)` and standard Ubuntu
desktop utilities. It contains tracked desktop startup and session launchers,
login glue, physical-input mapping, display controls, rotation, Power handling,
automatic shallow suspend, the extension source, and the narrow udev/polkit
rules used by those components.

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
Three isolated tests cover unsafe symlink rejection, atomic compilation while
preserving another extension, and the matching-digest no-recompile path.

## Remaining package boundary

This package is intentionally source-only and architecture-independent. A
complete release root still needs separately reproducible native compatibility
libraries and daemons, plus a local package generated from the owner's exact
matching Samsung firmware where redistribution is not permitted. The retained
recovery environment and full wipe/install/return-to-stock rehearsal also
remain release gates.
