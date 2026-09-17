# Native Android and Ubuntu dual boot

## Decision

Waydroid is not the end-user Android path for the SM-T630. It boots, runs GAPPS,
and survives restarts, but Android SurfaceFlinger renders through llvmpipe. The
owner rejected the UI as unusably slow even at the reduced 1024×623 target.
Native Android is the only currently credible way to retain the tablet's Adreno
acceleration and normal Android application experience.

This design adapts the boot-set approach from the Tab S9 Ultra reference port.
Its images and partition scripts are not compatible with this tablet; only the
architecture is reused.

## Evidence from the development tablet

The following read-only facts were rechecked on 2026-09-16:

- internal UFS exposes 248,799,232 512-byte sectors;
- partition 34 starts at sector 21,880,832 and occupies 226,918,360 sectors;
- partition 34 is currently an ext4 Ubuntu root labelled by GPT as `userdata`;
- the filesystem is clean, has 28,364,795 4 KiB blocks, and has an estimated
  minimum shrink size of 9,836,055 blocks;
- approximately 71 GiB is free in the mounted Ubuntu filesystem;
- Samsung's `super`, `recovery`, `vendor_boot`, DTBO, VBMETA, and bootloader
  partitions remain outside partition 34;
- the exact DZE3 factory archive and extracted stock `boot.img` are available
  locally for recovery; and
- Waydroid is stopped, while its data remains intact.

No partition table, filesystem, boot partition, Android data, or recovery
partition was changed during this investigation.

## Proposed installed layout

The conservative candidate preserves the beginning of the current Ubuntu
filesystem and divides only the existing final partition extent:

| Partition | Proposed extent in 512-byte sectors | Approximate capacity | Purpose |
| --- | ---: | ---: | --- |
| 34 `linuxroot` | 21,880,832–156,098,559 | 64 GiB | Existing Ubuntu ext4 root after an offline shrink |
| 35 `userdata` | 156,098,560–248,799,191 | 44.2 GiB | Fresh native Android data |

Both starts are 1 MiB aligned. The 64 GiB Ubuntu target is substantially above
the current estimated 37.6 GiB filesystem minimum. Exact free-space and
filesystem checks must be repeated from the maintenance image immediately
before any write; these numbers are a reviewed plan, not permission to alter
the tablet.

Android's read-only operating-system partitions remain in `super`. A stock
Android boot would discover the new partition by its `userdata` GPT name. The
existing partition 34 would be renamed `linuxroot`, and the Ubuntu initramfs
would locate it by that name plus the existing filesystem UUID and installation
marker instead of assuming `/dev/sda34` is called `userdata`.

## Boot switching

Unlike the SM-X910 reference, this port deliberately keeps Samsung's stock
`vendor_boot` and DTBO for Ubuntu. The two operating systems therefore need
different `boot` images but can share the already installed disabled-verification
VBMETA and the untouched supporting partitions:

- **Ubuntu set:** the accepted SM-T630 kernel plus the project initramfs;
- **Android set:** an exact DZE3 Android boot image, optionally Magisk-patched
  only after its original has been backed up and verified.

A switcher must verify the selected image's model, size, and SHA-256, write only
BOOT, read the complete partition back, compare it, and reboot only after a
match. It must never rewrite VBMETA during routine switching: Android's data
encryption is tied to verified-boot state, and changing that state can make
`/data` unreadable.

Ubuntu can expose the operation through Tablet Controls and a narrow privileged
helper. Android cannot write BOOT as an ordinary application; returning without
a computer therefore requires a deliberately rooted Android installation and a
small audited switcher. Until that application is ready, Download Mode plus the
Mac remains the recovery route.

## Required implementation gates

1. Build a RAM-only maintenance image containing pinned ARM64 `e2fsck`,
   `resize2fs`, and GPT tooling. It must not mount partition 34 automatically.
2. Add a read-only preflight that checks the exact model, build, kernel, disk
   geometry, GPT names and GUIDs, filesystem UUID/state/minimum, battery/external
   power, factory archive, and BOOT/recovery hashes.
3. Save and verify the primary and backup GPT plus BOOT, recovery, vendor_boot,
   DTBO, and VBMETA before changing storage.
4. Rehearse the complete shrink and GPT transaction against a byte-for-byte
   disposable disk image. Test interruption after every stage and prove the GPT
   backup restores it.
5. Offline-check and shrink ext4 to 64 GiB before shortening its partition.
   Never change the partition boundary first.
6. Rename partition 34 to `linuxroot`, create partition 35 as `userdata`, reread
   the table, and verify every protected partition is byte-for-byte unchanged.
7. Boot the revised Ubuntu image first and pass the normal desktop, storage,
   restart, power-off, suspend, camera, and input checks from `linuxroot`.
8. Use stock recovery to initialize only the new Android `userdata`, then boot
   the saved Android image and complete Android setup.
9. Build and validate BOOT switchers on both systems. A failed write must never
   reboot; recovery must remain reachable throughout.
10. Only after repeated cold switches and forced-failure recovery should dual
    boot become part of the public installer.

## Rejected shortcuts

- More Waydroid resolution reduction: measured improvement did not make the
  physical experience usable.
- Android in a virtual machine: Waydroid already has native CPU execution; a VM
  does not solve the absent compatible GPU path and adds overhead.
- Loop-backed Android `/data` inside Ubuntu: the stock Android fstab requires
  F2FS metadata encryption and inline-crypto settings tied to the UFS device.
  Replacing that with a loop device also requires a modified first-stage mount
  policy, making it less stock and less recoverable than a real partition.
- Rewriting BOOT manually for everyday use: a verified switcher transaction is
  required before the feature is suitable for users.

The reference design is documented in the inspiration project's
[`dual-boot.md`](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/blob/master/docs/dual-boot.md).
