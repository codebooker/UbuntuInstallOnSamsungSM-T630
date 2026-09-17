# Dual-boot maintenance preflight acceptance (2026-09-16)

## Scope

This cycle tested the RAM-only environment needed before any filesystem shrink
or GPT change. It did not resize a filesystem, alter the partition table, create
Android data, boot Android, or erase Waydroid. The only persistent write was a
temporary, verified BOOT replacement followed by restoration of the exact
accepted Ubuntu BOOT.

## Candidate

`tools/build_dualboot_maintenance.py` built a 100,663,296-byte Android boot-v3
image around the accepted v13 kernel. Its ramdisk contains pinned Ubuntu Noble
ARM64 builds of `e2fsck` 1.47.0, `resize2fs` 1.47.0, and `sgdisk` 1.0.10 plus
their exact libraries. Every private build input is hash-pinned and remains
ignored by Git.

The candidate SHA-256 was
`23741ac3a8b7bffd16ef63e95626b6aded6da40ec5964e2e32d1d13796a3a425`.
AVB footer verification passed. Startup creates only proc, sysfs, devtmpfs,
configfs, and RAM tmpfs mounts. It does not mount an internal block device and
does not run the preflight automatically.

The ramdisk embeds the exact accepted Ubuntu BOOT, SHA-256
`1403afb30d584418ea6bfc011317f33bf8073294eae355d0c05d8d61c7355e76`.
Its recovery helper requires external power, exact model/partition geometry,
the embedded hash, and an explicit RAM authorization token. It can write only
BOOT and refuses to reboot automatically.

## Pre-write gates

The tablet was externally powered at 100%. The stager verified the current
Ubuntu BOOT, recovery, vendor_boot, DTBO, VBMETA, model, kernel, target size,
candidate, and manifest before writing. It retained a verified transaction
rollback copy. A malformed recovery hash introduced while authoring the new
stager was rejected by `sha256sum` during `--check`; it was corrected to the
previously accepted project constant and the complete no-change check then
passed. No device write occurred on the rejected check.

The maintenance BOOT write and full readback matched. All neighboring protected
partition hashes remained unchanged.

## Physical preflight

The expected USB maintenance console appeared. Both modes passed:

```text
DUALBOOT_PREFLIGHT_PASSED_NO_DEVICE_WRITE minimum_blocks=9846776 target_blocks=16777216 battery=100
```

The quick mode checked exact model/kernel, the 4096-byte GPT logical sector,
sysfs's 512-byte geometry, partition names and sizes, absence of mounts and
holders, ext4 magic/UUID, GPT entry 34, GPT integrity, protected partition
hashes, and the ext4 shrink estimate. The deep mode additionally completed
`e2fsck -fn` without requesting a repair.

The unmounted estimate was 9,846,776 4 KiB blocks. The reviewed 64 GiB target
contains 16,777,216 blocks, leaving 6,930,440 blocks of margin. This supersedes
the earlier mounted estimate without changing the proposed boundary.

## Restoration and return

The embedded restore helper's no-write check passed, then its explicitly
authorized BOOT restoration wrote and reread the full partition successfully.
After a manual restart:

- BOOT matched the exact pre-cycle Ubuntu hash;
- partition 34 still began at sysfs sector 21,880,832, retained 226,918,360
  sysfs sectors, and remained named `userdata`;
- no partition 35 existed;
- Ubuntu mounted the original ext4 root;
- GNOME and Wi-Fi returned;
- Waydroid remained stopped; and
- `dpkg --audit` and `apt-get check` passed.

The rejected v2 staging artifact was removed from the tablet after its exact
hash was checked. The physically accepted v3 artifact and its transaction
rollback remain for recovery and further review.

This completes only the read-only maintenance gate. Offline shrink/GPT
rehearsal against a disposable disk image is next; it is not authorization to
change the tablet's storage.

## Dual-layout fail-safe follow-up

After the backward-compatible Ubuntu BOOT passed its own physical cold boot,
maintenance v4 replaced v3's embedded restore image with that exact accepted
dual-layout BOOT. V4 BOOT SHA-256 was
`f4299f215ec908d1b8117ec364c08baf6125f652e87e47658cd549e55badce4e`.

The v4 BOOT-only staging checks and complete readback passed. Its physical
preflight again passed without a device write; the later live minimum was
9,920,357 blocks, still 6,856,859 blocks below the 64 GiB target. The embedded
restore no-write check passed, then the explicitly authorized helper restored
the exact dual-layout BOOT, verified the complete BOOT readback, and returned
to Ubuntu after a manual restart. V4 supersedes v3 as the maintenance image for
future dual-boot work.
