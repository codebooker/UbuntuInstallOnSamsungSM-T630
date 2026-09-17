# Clean-install kernel correction — 2026-09-17

## Result

The explicitly authorized clean install completed against the existing split
layout. The installer formatted only p34 `linuxroot`, extracted the sealed
identity-clean Ubuntu root, verified the installed tree, and completed a clean
offline filesystem check. Android p35 was not formatted or mounted.

The first reboot found a release integration defect before owner setup. The
sealed dual-layout BOOT used the retired v13 Waydroid kernel, while the clean
root correctly contained the stock-assets package's module-compatible v12
modules. Kernel symbol-version checks therefore rejected `sec_tsp_log.ko` and
the dependent tablet startup path could not complete. The earlier development
root had hidden this mismatch because it still carried an incrementally staged
v13 module payload.

## Correction

Dual-layout Ubuntu BOOT v2 uses the physically proven v12 kernel with the same
restricted whole-disk/split-layout initramfs. Its exact properties are:

- BOOT SHA-256: `fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`
- kernel SHA-256: `7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6`
- size: 100,663,296 bytes
- accepted root: p34 `linuxroot`, 134,217,728 512-byte sectors

A recovery-console updater required the exact old BOOT, exact new BOOT,
model/build/kernel, partition identity and size, battery, and protected-neighbor
hashes. It wrote only p19 BOOT, re-read the complete partition, and reported
`DUAL_LAYOUT_BOOT_V2_WRITTEN_READBACK_VERIFIED`.

The subsequent reboot loaded the packaged touchscreen and WLAN modules and
reached the dark first-boot GNOME UI. The ownerless state remained intact:
there was no human account and `machine-id` was empty while the setup UI ran.

## Release hardening

- The dual-layout and maintenance builders now pin the module-compatible v12
  kernel and corrected Ubuntu BOOT.
- Maintenance v5 embeds BOOT v2 as its exact recovery image.
- Desktop 0.1.11 and release-base 0.1.20 pin the corrected Ubuntu switch hash.
- The private installer builder now requires a Magisk-patched Android BOOT,
  installs both switch images root-only, and seals their hashes in the rootfs
  manifest. It still refuses to create the Android-data acceptance marker;
  that marker requires physical encrypted-Android acceptance.
- The live clean root's restored private switch assets pass the complete
  read-only Ubuntu-side native-Android preflight.

The corrected identity-clean root was then cloned before owner creation,
audited, and archived. The final private root archive is 1,274,364,467 bytes,
contains 84,688 members, and has SHA-256
`7bbd12374677144ddcab7542c3f3dd6bd00dd33219ac604f069cb920e805bac1`.
Its manifest records desktop 0.1.11, release-base 0.1.20, the accepted rooted
Android BOOT hash, and Ubuntu BOOT v2. The complete six-input installer bundle
was sealed, immediately reverified against `SHA256SUMS`, and retained on p34;
the disposable 3.6 GB build clone was removed afterward.

The remaining physical acceptance item is a post-setup button round trip using
the corrected image on both sides.
