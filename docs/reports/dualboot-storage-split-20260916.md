# Physical dual-boot storage split (2026-09-16)

The development SM-T630 now boots Ubuntu from the installed 64 GiB
`linuxroot` partition and exposes a separate, still-unformatted 44.2 GiB
`userdata` partition for native Android. Only the former final partition extent
was divided; Samsung's operating-system, bootloader, recovery, and metadata
partitions were not relocated.

Before any device write, maintenance v4 passed both quick and deep preflight.
The measured ext4 minimum was 9,944,888 4 KiB blocks, below the 16,777,216-block
target. The physical GPT was exported, SHA-256 verified after transfer to the
Mac, and kept in Git-ignored local storage. Replaying that exact Samsung GPT on
a 127,385,206,784-byte sparse disk proved the proposed split, preservation of
entries 1–33, GPT verification, and byte-for-byte restore of the original
table.

`maintenance/apply-dualboot-split` then performed two separately authorized
phases:

1. `e2fsck -p` accepted the unmounted Ubuntu filesystem, `resize2fs` reduced it
   to exactly 16,777,216 blocks, a second filesystem check passed, and a fresh
   GPT export remained byte-for-byte identical to the host-saved backup.
2. GPT partition 34 retained its unique GUID but became Linux `linuxroot` at
   4 KiB sectors 2,735,104–19,512,319. Partition 35 became Android
   `userdata` at sectors 19,512,320–31,099,898. Kernel-visible 512-byte sizes
   are 134,217,728 and 92,700,632 sectors respectively.

The first split attempt demonstrated the automatic rollback path. Linux
reassigned partition minors after rereading the table, while the minimal
maintenance `/dev` retained an old node. The verifier therefore rejected a
false ext4-magic result and restored the exact original GPT before returning an
error. A freshly constructed device node proved the filesystem was intact and
the rollback GPT matched the host backup byte-for-byte. The transaction helper
was corrected to construct every block node from current sysfs major/minor
values after each table reread, then its unit and BusyBox syntax tests passed.

The corrected attempt passed GPT verification, an offline ext4 check, a
read-only mount and installation-marker check, and before/after hashes of
recovery, `vendor_boot`, DTBO, and VBMETA. A second exact GPT backup of the
accepted split was transferred to Git-ignored host storage.

After a clean maintenance reboot, the embedded dual-layout Ubuntu BOOT was
restored with a full-partition readback match. Ubuntu then returned with:

- accepted BOOT SHA-256
  `eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb`;
- `/dev/sda34` mounted as 64 GiB ext4 `linuxroot`, with approximately 27 GiB
  free;
- `/dev/sda35` present as the unformatted Android `userdata` extent;
- GNOME Shell and Wi-Fi/default routing active;
- the installation marker and GPT verification passing; and
- `dpkg --audit` empty.

Waydroid remains installed only as retained test data. Its session is stopped,
and `/etc/t630/waydroid.disabled` prevents the non-systemd desktop startup from
launching its coordinator or profile supervisor. No Waydroid data was deleted.

Native Android initialization, stock Android boot acceptance, and audited BOOT
switchers remain separate gates. Partition 35 must not be formatted from
Ubuntu merely because the geometry is now ready; stock recovery's exact wipe
scope must be proven first.
