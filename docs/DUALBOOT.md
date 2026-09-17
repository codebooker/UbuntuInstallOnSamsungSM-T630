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

The following facts were rechecked after the authorized storage transaction on
2026-09-16:

- internal UFS exposes 248,799,232 512-byte sectors;
- partition 34 starts at sector 21,880,832, occupies 134,217,728 sectors, and
  is the 64 GiB ext4 Ubuntu root labelled `linuxroot`;
- partition 35 starts at sector 156,098,560, occupies 92,700,632 sectors, and
  is the stock-recovery-created 44.2 GiB F2FS Android `userdata` extent;
- the Ubuntu filesystem is clean, has exactly 16,777,216 4 KiB blocks, and has
  approximately 27 GiB free;
- Samsung's `super`, `recovery`, `vendor_boot`, DTBO, VBMETA, and bootloader
  partitions remain outside partition 34;
- the exact DZE3 factory archive and extracted stock `boot.img` are available
  locally for recovery; and
- the rejected Waydroid packages, images, owner data, launchers, backups, and
  kernel-trial artifacts were removed after native button switching passed.

The exact pre-split and post-split GPT backups remain private local recovery
artifacts and are deliberately excluded from Git.

## Installed layout

The conservative layout preserves the beginning of the Ubuntu filesystem and
divides only the former final partition extent:

| Partition | Installed extent in 512-byte sectors | Approximate capacity | Purpose |
| --- | ---: | ---: | --- |
| 34 `linuxroot` | 21,880,832–156,098,559 | 64 GiB | Existing Ubuntu ext4 root after an offline shrink |
| 35 `userdata` | 156,098,560–248,799,191 | 44.2 GiB | Stock-recovery-created F2FS native Android data |

Both starts are 1 MiB aligned. Immediately before the shrink, the maintenance
image measured a 9,944,888-block minimum against the 16,777,216-block target.

Those values use Linux sysfs's conventional 512-byte sector units. Samsung's
UFS exposes a 4096-byte logical sector to GPT tools, so the corresponding
`sgdisk` coordinates are 2,735,104–19,512,319 for partition 34 and
19,512,320–31,099,898 for partition 35. `tools/plan_dualboot_layout.py` emits
both forms and rejects boundaries that cannot be converted exactly. A writer
must use the units reported by its own tool; confusing these two coordinate
systems would be destructive.

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

The end-user interface is deliberately button-only:

- Ubuntu exposes **Restart into Android** in Quick Settings and Tablet Controls.
  A dark confirmation dialog calls one exact passwordless `sudo` command; its
  sudoers rule cannot authorize a shell or any other helper argument.
- Android exposes a standalone **Restart into Ubuntu** launcher. After its own
  confirmation dialog, it calls one root-owned helper through Magisk. The helper
  defaults to a read-only check and performs a write only with the exact
  `--switch-and-reboot` argument.

Neither path asks the owner to open a terminal or type a command. Both validate
the model, build, installed layout, selected image, current BOOT, protected
neighbors, battery state, and rollback image before changing anything. The
Android button and its narrow rooted service are installed and locally signed.
On 2026-09-17, both touchscreen paths completed a physical Ubuntu to Android to
Ubuntu round trip. Android retained encrypted `/data`, Samsung Notes, Magisk,
and the launcher; Ubuntu returned on the exact accepted BOOT with GNOME and its
reverse switch still ready. Download Mode plus a host remains the recovery route,
not the normal switching interface. See the
[button-only round-trip report](reports/native-button-dualboot-20260917.md).

For a corrected Ubuntu BOOT generation, `tools/update_android_switch_payload.py`
updates Android's private Ubuntu image and fixed root helper over an already
authorized USB-debugging connection. It defaults to a no-change check. Its
explicit `--apply` path validates the exact Android model/build, encrypted data,
currently installed rooted Android BOOT, old-or-current Ubuntu generation, and
new payload hashes; it atomically replaces only files below `/data/adb/t630`.
It never opens or writes a partition.

After Magisk patching, the Ubuntu-side artifact is the accepted patched Android
BOOT rather than the factory BOOT. Its root-owned `boot.sha256` is checked before
every switch. Android independently pins the currently installed patched BOOT
hash before replacing it with Ubuntu. This preserves the Android service across
round trips while keeping the untouched factory BOOT as the Download Mode
recovery image.

`tools/restore_ubuntu_boot_download_mode.sh` implements the temporary Ubuntu
recovery route. `tools/flash_accepted_android_boot_download_mode.sh` provides the
equivalent guarded Android BOOT route used for initial Magisk installation. Each
default `--check` mode validates only local artifacts. The explicit
write mode requires the accepted 96 MiB Ubuntu BOOT hash, Heimdall 2.2.2, exact
authorization text, a detected Download Mode device, and a freshly downloaded
live PIT whose BOOT entry is identifier 19 with 24,576 4 KiB blocks. It then
flashes only `BOOT`, without repartitioning or bypassing Heimdall's size check.
The running target must verify the complete BOOT hash again after returning.

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

The Ubuntu and Android launchers do not contain firmware or private tablet
state. `t630-os-switcher` declares no Android permissions and has no network
permission. Its signing key and generated APK are local release artifacts, not
committed to the repository. Root is confined to the fixed helper path; the app
does not accept commands or paths from its UI.

Gate 1 now has a physically accepted v3 image. Its init mounts no block device,
its preflight has no write mode, and its exact Ubuntu `boot.img` is embedded as
a compressed fail-safe. A separate guarded recovery helper can restore only
that pinned BOOT after an explicit RAM token and verifies the full partition
readback; it cannot touch the GPT or either data partition. The ARM64 tools ran
successfully first from an isolated RAM staging directory and then from the
physical maintenance boot. Both quick and deep preflight passed; the deep run
used `e2fsck -fn`. The embedded Ubuntu BOOT was restored with a complete
readback match, and the normal desktop, Wi-Fi, original partition geometry,
and clean package state returned. See the
[maintenance acceptance report](reports/dualboot-maintenance-preflight-20260916.md).

Gate 4's exact-geometry sparse rehearsal also passes. The test creates a
127,385,206,784-byte logical disk with a 4096-byte sector, uses only a few MiB
of real host storage, preserves a filesystem marker through the 64 GiB shrink
and split, verifies both proposed partition sizes, restores the saved GPT, and
mounts the preserved filesystem again. The sparse image is deleted on success.
See the [sparse rehearsal report](reports/dualboot-sparse-rehearsal-20260916.md).

The backward-compatible Ubuntu BOOT prerequisite also passes physically on the
unchanged whole-disk layout. Its initramfs accepts only partition 34 with either
the exact current `userdata` geometry or the exact proposed `linuxroot`
geometry, then independently requires the existing ext4 UUID and installation
marker. The accepted image returned GNOME, Wi-Fi, package health, and the
unchanged full-size root after a cold boot. See the
[dual-layout boot report](reports/dual-layout-ubuntu-boot-20260916.md).

Maintenance v5 embeds the corrected module-compatible dual-layout BOOT v2 as
its fail-safe. The image is built from the proven v12 kernel because its symbol
versions match the packaged DZE3 modules; the retired v13 Waydroid kernel does
not. BOOT v2 completed a guarded physical BOOT-only write and full readback,
then reached the clean first-boot GNOME UI with the packaged modules loaded.
Maintenance v5 supersedes v4 for any future storage operation.

Gates 3, 5, 6, and the storage/boot portion of gate 7 now pass physically.
`maintenance/apply-dualboot-split` requires a host-verified exact GPT backup,
external power, two separate RAM-only authorization tokens, exact model and
geometry, unmounted storage, and pinned protected-partition hashes. It shrinks
ext4 before touching GPT and arms automatic GPT rollback until the split has
passed all checks. The final Ubuntu boot from `linuxroot` returned GNOME,
Wi-Fi, the exact accepted BOOT hash, a clean package audit, and a valid GPT.
See the
[physical storage split report](reports/dualboot-storage-split-20260916.md).

The stock-recovery portion of gate 8 now also passes physically. A non-wiping
BCB preflight first proved the otherwise headless DZE3 recovery path and its
automatic command clearing. A separately hashed and authorized wipe BCB then
caused stock recovery to resolve `/data` by the `userdata` GPT name, create
F2FS on p35 with Android quota/casefold/compression features, recreate ext4
`metadata`, report a complete wipe, and reboot. Ubuntu returned from unchanged
p34, all protected image hashes still matched, GPT verified, and a read-only
F2FS check passed. See the
[native Android storage report](reports/native-android-storage-init-20260916.md).
The exact stock Android BOOT then passed its complete no-write gate and an
atomic BOOT-only write/readback; first-boot display and Android setup acceptance
subsequently passed as well. Android mounted encrypted F2FS `/data` through a
`dm-default-key` mapping, used the Adreno 642L renderer, and ran Samsung Notes
with working S Pen strokes. After first boot, raw p35 is ciphertext and must not
be given to `fsck.f2fs`; the repeat Ubuntu-to-Android helper explicitly enforces
that boundary. The guarded Download-Mode return restored only the accepted
Ubuntu BOOT, whose complete readback matched after GNOME and Wi-Fi returned.
See the
[native Android first-boot report](reports/native-android-firstboot-20260916.md).

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
