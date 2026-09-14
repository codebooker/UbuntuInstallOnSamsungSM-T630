# Reproducible persistent boot candidate (2026-09-14)

## Result

`tools/build_boot_persistent.py` now produces the persistent release boot image
from tracked current initramfs sources instead of copying the historical v1
ramdisk. It pins and verifies:

- exact DZE3 stock boot metadata;
- the accepted module-compatible ARM64 kernel, SHA256
  `7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6`;
- the static Ubuntu ARM64 BusyBox payload;
- every tracked initramfs source;
- Android boot header v3 metadata, packed kernel and ramdisk bytes, the
  96 MiB boot-partition size, and the AVB hash footer.

The initramfs includes the bounded non-systemd Wi-Fi/remote fallback and embeds
the complete tested shutdown helper immediately. Safe camera and desktop
cleanup therefore no longer depends on Wi-Fi first replacing an older minimal
helper.

Two independent builds produced byte-identical gzip ramdisks and boot images.
The candidate is exactly 100,663,296 bytes with SHA256
`1462fb6f5f97a347a6c9bba231b479dc1d17f13617dfc6ec78149c00afe85fff`.
Its compressed ramdisk SHA256 is
`8e777a136d9d1b27d9f15fd9c2119dc9f9e6fce40050aa3bd6cde311e3d57fe8`.
Unpacked verification scratch files are removed after all comparisons; the
final output retains only the 96 MiB `boot.img` and its small manifest.

## Write boundary

The builder performs no device I/O and marks the artifact not flash-approved.
`tools/write_release_boot_v1.sh` is a separate exact-device writer. Its default
mode is read-only: it checks model, kernel, installed marker, boot partition
name and size, charge state, candidate size/hash, and the exact currently
installed boot hash. Write mode targets only `/dev/sda19`, verifies its complete
readback, and then verifies vendor_boot, init_boot, dtbo, and vbmeta unchanged.

Physical write and cold-boot acceptance are separate gates.
