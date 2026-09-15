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

## Physical acceptance

The writer's read-only mode first passed against candidate SHA256 `1462fb6f…`
and the installed boot SHA256 `5394a234…`. Write mode then changed only
`/dev/sda19`, verified its complete readback as `1462fb6f…`, and verified
vendor_boot, init_boot, DTBO, and vbmeta byte-for-byte unchanged.

Cold boot `e1dbba7d-b920-49e3-884c-fbf24821b4f6` mounted the persistent Ubuntu
root and exposed the USB recovery console. Full BOOT readback and both embedded
startup/helper hashes matched the manifest. Without USB intervention, Qualcomm
Wi-Fi connected and the new fallback launched SSH and the screen service in
about one minute.

The post-boot health sweep found Weston, GNOME, NetworkManager, Bluetooth,
PipeWire speakers and microphone, sensor proxy, battery reporting, and expected
device permissions healthy, with zero targeted kernel-fault markers. The
embedded full shutdown helper then completed a second clean restart. Boot
`1a5ab32d-9d13-49ab-94dd-b833faed1ff4` again brought up Wi-Fi and SSH
automatically and passed the same health sweep with the boot image and both
initramfs helper hashes unchanged.

The persistent release boot image is physically accepted on the development
SM-T630. Installing the identity-clean release root and rehearsing return to
stock remain separate gates.

## One-shot clean-root follow-up

The accepted image was extended with a strictly bounded one-shot selector for
`/opt/t630/rehearsal/release-root`. The selector validates the fixed directory,
offline-root marker, device install marker, and absence of symlinks. It is
renamed to `.t630-next-root.consumed` and synced before control enters the
candidate, so any later restart returns to the normal known-good root.

Candidate v2, SHA256
`ce279665976b877bc1442d9c027963f5774a8a7e60d4935072bfea7544ec3c14`,
passed full write/readback and neighboring-partition checks. Boot
`4830399a-df90-49eb-84b9-6da9cccdbcbb` selected the preserved 3.1 GB clean
root and consumed the selector. The USB console independently reported the
selected root. Weston then exposed two clean-install defects rather than
silently falling back to personalized state: the `t630-owner` system group had
to exist before the account wizard, and `wpasupplicant` had to be explicit
when installing public dependencies without recommends. Both fixes are now
owned by the deterministic packages/provisioner.

Candidate v3, SHA256
`2d9ebe83d1bbc3d3f1495c5004fd06a8e3a250782ba00a1b5416df2542d5acc4`,
adds an ownerless clean-root exception to the orderly shutdown helper while
retaining the exact fixed path and offline marker checks. The exact prior v2
artifact is preserved on tablet storage. V3 full readback passed,
and vendor_boot, init_boot, DTBO, and vbmeta remained byte-identical. This
changes no running process and awaits its cold-boot acceptance after the
current first-boot walkthrough.
