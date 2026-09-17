# Native Android first boot and Ubuntu return (2026-09-16)

The physical SM-T630 completed its first native stock Android boot from the
split layout. The only boot-chain change was an exact DZE3 `boot.img` written
to BOOT after a guarded no-write gate and a complete accepted-Ubuntu BOOT
rollback backup. Recovery, `vendor_boot`, DTBO, VBMETA, `super`, and both data
partition boundaries were unchanged.

## Android acceptance

The owner completed normal Samsung setup, enabled Developer options, and
authorized USB debugging. ADB then reported:

- exact model SM-T630 and stock DZE3 Android 15 release fingerprint;
- completed boot animation and `sys.boot_completed=1`;
- orange unlocked verified-boot state;
- encrypted file-based `/data`, mounted read/write as F2FS through a
  `dm-default-key` device;
- approximately 41 GiB free on the 44 GiB Android data filesystem;
- enforcing SELinux;
- Qualcomm Adreno 642L OpenGL ES 3.2 rendering;
- working 1920×1200 output, touch/S Pen input registration, three camera
  devices, audio service, sensors, charging, Wi-Fi, and Internet routing; and
- installed Samsung Notes, Google Play services, and Play Store packages.

A private, Git-ignored 1920×1200 screenshot showed Samsung Notes full-screen
with the owner's continuous S Pen strokes. This proves the stock accelerated
application path, display, and pen together; no owner drawing or screenshot is
published. Samsung Notes' live graphics counters reported 529 frames, a 15 ms
median, 34 ms 90th/95th percentiles, and 6.99% modern jank. This is not a formal
benchmark, but it clearly separates native Adreno rendering from the rejected
Waydroid llvmpipe path.

## Metadata-encryption boundary

Before Android's first boot, stock recovery's plaintext F2FS could be checked
from Ubuntu. After Android initialized file-based encryption, `/data` was
mounted from a device-mapper target rather than raw p35. Back in Ubuntu, raw
p35 correctly appeared as ciphertext and no longer exposed F2FS magic or a
filesystem type. Passing the raw partition to `fsck.f2fs` therefore reports no
superblock and is invalid after first boot; it is not evidence of corruption.

`tools/switch_to_native_android.sh` encodes that distinction. It requires the
root-owned physical-acceptance marker, exact split geometry, opaque and
unmounted raw p35, ext4 `metadata`, an empty BCB command, exact accepted Android
and Ubuntu BOOT images, power, GPT verification, and all protected-neighbor
hashes. It never runs a filesystem checker on encrypted p35. Its write mode
touches only BOOT, verifies the complete readback, and restores the accepted
Ubuntu BOOT automatically on any failure.

## Android-to-Ubuntu return

With Android USB debugging authorized, `adb reboot download` entered Samsung
Download Mode without button timing. The Mac-side guarded return helper then:

1. verified Heimdall 2.2.2 and the exact 96 MiB accepted Ubuntu image;
2. downloaded the live PIT while keeping the same session open;
3. required BOOT identifier 19 and 24,576 4 KiB blocks;
4. uploaded only BOOT, without repartitioning or a size-check bypass; and
5. allowed Heimdall to reboot the tablet.

Ubuntu returned after its normal stock Wi-Fi startup delay. Complete readback
matched the accepted Ubuntu BOOT SHA-256. Recovery, `vendor_boot`, DTBO, and
VBMETA also matched; p34 remained the mounted `linuxroot`; p35 retained its
exact `userdata` geometry; the BCB was clear; GPT verification passed; GNOME
and Wi-Fi were active; and `dpkg --audit` plus `apt-get check` were clean.

## Remaining switch acceptance

The accepted-encrypted-data switcher subsequently passed its no-write gate and
wrote/read back the exact stock Android BOOT for a second boot. The tablet
rejoined Wi-Fi, proving Android booted, while USB debugging remained unavailable
at the pre-unlock state. Unlock/ADB confirmation of persisted Notes data and a
second Download-Mode return remain the final checks for this cycle.
