# Dual-boot sparse-disk rehearsal (2026-09-16)

`tools/test_dualboot_layout_docker.sh` completed the exact proposed storage
transaction against a disposable sparse regular file. No tablet device was
opened. The file's logical size was 127,385,206,784 bytes, matching internal
UFS, while its peak host allocation reported after the complete transaction was
only 6.2 MiB. The test deletes the sparse image on success.

The isolated Ubuntu 24.04 container attached the file through a loop device
with a 4096-byte logical sector and confirmed the equivalent 248,799,232
512-byte sysfs sectors. It then:

1. created partition 34 at GPT sectors 2,735,104–31,099,898 with Android
   userdata type and name;
2. built a 4 KiB-block ext4 filesystem with the release UUID and wrote a marker;
3. checked the unmounted filesystem and shrank it to exactly 16,777,216 blocks;
4. saved a GPT backup and retained partition 34's unique GUID;
5. recreated partition 34 as 64 GiB `linuxroot` at
   2,735,104–19,512,319 with Linux type;
6. created partition 35 as 44.2 GiB Android `userdata` at
   19,512,320–31,099,898 with Android userdata type;
7. verified their kernel-visible sizes as 134,217,728 and 92,700,632
   512-byte sectors;
8. mounted the shortened Ubuntu partition and verified its marker;
9. restored the saved pre-split GPT; and
10. verified partition 35 disappeared, partition 34 returned to its original
    size/name, the marker remained, and `e2fsck -p` passed.

The transaction also establishes two non-destructive interruption boundaries:
before the resize, nothing has changed; after the filesystem shrink but before
the GPT write, ext4 is simply smaller than its still-original partition. After
the split, the saved GPT can restore the table, although the filesystem remains
safely at its smaller size until explicitly regrown.

This rehearsal validates geometry, filesystem preservation, and GPT rollback
logic. It does not model 35 GiB of real file placement, Samsung's undersized GPT
entry array warnings, a power loss during a sector write, or Android's first
format/encryption setup. Those remain device-side gates, not assumptions.
