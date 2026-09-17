# Dual-layout Ubuntu BOOT acceptance (2026-09-16)

Ubuntu's previous initramfs required partition 34 to be named `userdata` and to
retain its original full size. That image would correctly refuse to boot after
the proposed split renamed and shortened the partition, so it had to be
replaced before any storage operation.

`persistent/start-ubuntu` now accepts exactly two identities:

- partition 34, GPT name `userdata`, 226,918,360 512-byte sysfs sectors; or
- partition 34, GPT name `linuxroot`, 134,217,728 512-byte sysfs sectors.

Both paths still require the existing ext4 magic, filesystem UUID, and
SM-T630 installation marker. `/dev/sda35` is never considered an Ubuntu root.
Unexpected names, sizes, partition numbers, UUIDs, or markers stop before the
desktop starts.

`tools/build_dual_layout_boot.py` combined that ramdisk with the accepted v13
kernel and stock DZE3 boot-v3 metadata. The resulting 100,663,296-byte image,
SHA-256
`eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb`,
passed unpack/repack identity checks and AVB footer verification.

The BOOT-only stager checked the current BOOT, candidate, manifest, model,
kernel, power, partition target, and recovery/vendor_boot/DTBO/VBMETA hashes.
It retained a verified transaction rollback, wrote the new image, reread the
complete BOOT partition, and rechecked the protected neighbors.

The unchanged whole-disk layout then passed a cold boot. BOOT matched the new
hash, partition 34 remained full-size `userdata`, GNOME and Wi-Fi returned,
Waydroid remained stopped, and `dpkg --audit` plus `apt-get check` passed.

This proves backward compatibility before the split. The `linuxroot` branch
still requires physical acceptance after an authorized storage transaction.
