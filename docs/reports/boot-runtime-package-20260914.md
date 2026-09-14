# Host compositor runtime package (2026-09-14)

## Result

`tools/build_boot_runtime_deb.py` now builds the account-neutral desktop host
layer as a deterministic Debian package:

- name: `t630-boot-runtime_0.1.0_all.deb`
- size: 20,784 bytes
- SHA256: `7ec7c61eab7f12460bcf25d8bb3cfd528107a43742fd4dfca4abc1ed06a9dc1d`

Two builds with the same source epoch were byte-identical. The package depends
on the tested hardware runtime, Weston 13, Maliit, GNOME Shell 46, seatd,
chrony, Qt Wayland, and the Ubuntu icon/rendering libraries it actually uses.

## Owned integration

The package installs the Weston desktop configuration, chrony RAM-state policy,
keyboard mode, launcher renderer, Maliit icon aliases, and version-checked GNOME
lock-screen guards. The guards are generated only when GNOME's embedded source
hashes match the audited Ubuntu 24.04 build; an unexpected GNOME update fails
closed instead of applying an unreviewed patch.

The customized Weston keyboard and Maliit `qml/Keyboard.qml` use package-owned
`dpkg-divert` records. No distro package is overwritten anonymously. The
post-removal script restores both originals and removes only the exact generated
T630 assets.

## Clean-root acceptance

The package was installed into the preserved identity-clean Ubuntu Base root on
the physical tablet. Installation generated all three launcher PNGs and both
GNOME overlays, and Weston and Maliit had no unresolved native libraries. A
same-version reinstall completed successfully. Removal restored the original
Weston keyboard at SHA256
`5ad13717395993ef3591582b6ef595f3bba91e47d43029c1ffa970894c97f14a`
and Maliit keyboard at SHA256
`f194095e043173e69e0831bff46d41b5e2638ae04990dbc92aa2960b3a364fc0`.
Both diversions and generated files were absent afterward. Final reinstall and
the expanded eleven-package release check passed with an empty `dpkg --audit`,
clean identity audit, and no leaked mounts.

This closes the compositor/keyboard packaging boundary. It does not yet prove a
physical boot from the clean root; the initramfs still needs a guarded test image
that selects the preserved rehearsal subroot without replacing the known-good
live root.
