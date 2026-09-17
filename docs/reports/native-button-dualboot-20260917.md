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

- repeat cold cycles with USB detached after each verified write;
- exercise deliberate image, hash, power, and protected-neighbor failures and
  confirm that every one refuses the switch without rebooting; and
- include both launchers and their root-owned artifacts in the final clean-image
  installer acceptance.
