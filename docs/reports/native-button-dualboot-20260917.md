# Native button-only dual-boot acceptance — 2026-09-17

## Scope

This report records the first physical end-user round trip between the installed
Ubuntu system and stock Android 15 on the SM-T630. Normal operation used only
touchscreen buttons and confirmation dialogs. Host access was used afterward to
verify hashes and retained state, not to perform either routine switch.

## Installed switch paths

- Ubuntu exposes **Restart into Android** through Tablet Controls and the tablet
  GNOME assets. Its dark confirmation runs one exact passwordless sudo command.
- Android exposes the standalone **OS Switcher** launcher with **Restart into
  Ubuntu**. Its confirmation feeds one compile-time-constant helper invocation
  into an interactive Magisk root shell.
- Both helpers default to read-only checks, require the exact write argument,
  require external power and at least 50% battery, validate the SM-T630 model and
  installed layout, pin the current and replacement BOOT hashes, verify recovery,
  vendor_boot, DTBO, and VBMETA, and read back all 96 MiB before rebooting.

The interactive Magisk shell is necessary on this stock Samsung build because
the DEFEX path drops the root context when Magisk launches the system shell with
`su -c`. No UI text, path, or other user-controlled value is sent to that shell.

## Physical result

1. Ubuntu's confirmation was opened in the running GNOME session and its
   **Restart into Android** touchscreen button was pressed.
2. Android booted on the accepted Magisk-patched BOOT
   `b704f9ab0bfe89fca284699ae9f4cb5db12fa135aeb631b4b30a9a14b636c5be`.
3. Android reported completed boot with encrypted `/data`; the OS Switcher and
   Samsung Notes packages remained installed. The root helper returned
   `UBUNTU_SWITCH_READY`.
4. The Android launcher and confirmation were opened and the **Restart into
   Ubuntu** touchscreen button was pressed.
5. Ubuntu returned on accepted BOOT
   `eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb`.
   GNOME, SSH, and the guarded Android return helper were ready again.

No GPT, filesystem, VBMETA, recovery, vendor_boot, or DTBO write occurred during
the routine cycle. The host-side Download Mode tools remain recovery and initial
installation mechanisms only.

## Remaining endurance work

- include both launchers and their root-owned artifacts in the final clean-image
  installer acceptance.

## Module-compatible BOOT endurance correction

A later release-endurance cycle exposed that Android still retained the old v1
Ubuntu image and helper even though the Ubuntu-side switcher had advanced to the
module-compatible v2 image. Android correctly verified and wrote what it had,
but that image was SHA-256
`eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb`.
It boots the retired v13 kernel, whose symbol versions do not match the packaged
v12 touchscreen and WLAN modules. Ubuntu consequently stopped during early
startup before GNOME. Neither data partition was modified.

The recovery serial console restored only BOOT from the root-owned v2 image.
The recovery updater verified the full 100,663,296-byte write plus recovery,
`vendor_boot`, DTBO, and VBMETA before an orderly reboot. Ubuntu returned on
BOOT `fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`
with the v12 kernel, input modules, GNOME, Wi-Fi, audio, clean package state, and
zero checked kernel faults.

Inspection in Android proved `/dev/block/by-name/boot` resolves to
`/dev/block/sda19` and has the expected 98,304 KiB size. The installed private
Ubuntu image was v1 and the installed helper predated the v2 updater. The
updater then atomically replaced only those two root-owned files below
`/data/adb/t630`; it performed no partition write. The current helper additionally
requires the exact physical BOOT mapping and size, flushes the block device,
performs a delayed durable readback, and records a mode-0600 handoff journal
before requesting Android's orderly reboot.

The corrected Android payload contains Ubuntu BOOT v2 and helper SHA-256
`cc7dd9b2ff0c84295031c36bb94dfa534570fa9e75097030c3170b116aa30c60`.
Its complete read-only gate passed, then a second Android-to-Ubuntu transaction
reported `UBUNTU_BOOT_STAGED_READBACK_VERIFIED_RESTARTING`. Ubuntu returned on
v2 and again passed GNOME, Wi-Fi, the 30% unmuted speaker sink, Chrome's keyboard
watcher, `dpkg --audit`, `apt-get check`, the reverse-switch preflight, and a
zero checked-fault count. Malformed-mode requests on both sides were also
refused before any write.

The remaining physical refusal classes subsequently passed. A private mount
namespace presented the production Ubuntu helper with a bad selected-image
hash, simulated loss of external power, and a bad recovery-neighbor hash while
leaving the real files and devices untouched. Every check returned the expected
refusal status without rebooting. BOOT and all four protected neighbors were
rehashed after each case and remained exact. See the
[release refusal and recovery report](release-refusal-recovery-gates-20260917.md).
