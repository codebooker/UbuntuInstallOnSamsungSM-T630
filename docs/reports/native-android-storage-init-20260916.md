# Native Android storage initialization (2026-09-16)

The physical SM-T630's stock DZE3 recovery successfully initialized the new
partition 35 as Android `userdata` without altering Ubuntu partition 34 or any
boot-chain neighbor. This closes the destructive storage half of native
Android dual-boot gate 8.

## Recovery preflight

`tools/build_recovery_bcb.py` first produced a standard 2,048-byte Android
bootloader message containing only `boot-recovery`, the project-specific audit
reason, and `en-US`. The binary contained no wipe or format request. A guarded
stager required the exact model, installed build, split geometry, battery and
external power, GPT verification, accepted Ubuntu BOOT, and pinned recovery,
`vendor_boot`, DTBO, and VBMETA hashes. It also required a host-verified full
backup of the 1 MiB `misc` partition.

Stock recovery ran even though the panel remained black and recovery exposed no
ADB or USB function. Its persistent cache log proved that it parsed the audit
reason, ran in manual no-wipe mode, cleared the BCB, and waited at its default
`Reboot system now` item. The complete original `misc` image was subsequently
restored and matched its host SHA-256 byte for byte.

## Guarded initialization

Before the write, the complete 16 MiB `metadata` partition was copied to a
Git-ignored host artifact and SHA-256 verified. A distinct wipe BCB was then
built with exactly:

```text
recovery
--wipe_data
--reason=t630_dualboot_native_android_initialization
--locale=en-US
```

Its SHA-256 is
`bb26630239e7af8c098b4b0ed44074e29181ad4f7b28f73e726913afad948c89`.
`tools/stage_stock_recovery_wipe.sh` requires that exact binary, the exact
backups and host markers for both `misc` and `metadata`, a root-owned explicit
authorization token, the mounted 64 GiB `linuxroot`, the unmounted 44.2 GiB
`userdata` with no recognized filesystem, external power, a valid GPT, and all
pinned protected-image hashes. It writes only the first 2 KiB of `misc`, checks
the readback and unchanged remainder, and automatically restores the complete
saved `misc` on any staging error.

The first guarded invocation refused before writing because an overly broad
`blkid` check treated the partition's GPT identity as if it were a filesystem.
The guard was narrowed to request only `TYPE`; the target had no filesystem,
and the corrected focused tests passed. The second invocation staged and
verified the exact BCB. A clean reboot entered recovery and returned to Ubuntu
without user input.

## Physical results

The persistent stock-recovery log records:

- `/data` resolved to `/dev/block/bootdevice/by-name/userdata`;
- `should_wipe_data = 1` and `should_prompt_and_wipe_data = 0`;
- `make_f2fs` created the filesystem with Android mode, project quota, extended
  attributes, casefolding, UTF-8, and compression;
- the F2FS formatter returned zero;
- stock recovery recreated `metadata` as ext4;
- `Data wipe complete` was recorded; and
- recovery rebooted automatically after approximately two seconds.

After Ubuntu returned:

- p35 had F2FS magic `1020f5f2`, version 1.14, and a 47,462,707,200-byte
  filesystem;
- `fsck.f2fs --dry-run` reported all structural checks `Ok` and a clean,
  unmounted checkpoint;
- p25 retained ext4 magic and had changed from its pre-initialization hash, as
  expected after recovery recreated Android encryption metadata;
- the BCB command field was empty;
- p34 was still the mounted Ubuntu root;
- GPT verification reported no problems; and
- Ubuntu BOOT, recovery, `vendor_boot`, DTBO, and VBMETA still matched their
  accepted hashes exactly.

The exact partition backups, device-generated filesystem identity, factory
images, and authorization files remain private and Git-ignored.

## Next gate

The exact stock DZE3 BOOT passed the no-write Android acceptance gate and the
BOOT-only transaction saved a full accepted Ubuntu BOOT rollback before an
exact Android BOOT write/readback. Native Android first-boot display, setup,
and a Download-Mode return to Ubuntu remain separate physical acceptance
steps. Routine switching will not be published until both sides have audited
BOOT-only helpers and repeated failure recovery has passed.
