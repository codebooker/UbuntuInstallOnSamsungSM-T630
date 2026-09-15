# Clean-root restart, owner folders, and Wi-Fi ordering — 2026-09-15

Selected root remained `/run/ubuntu/opt/t630/rehearsal/release-root` after the
normal owner's `t630-display power restart` request. Boot ID changed from
`2dc5b3c3-b305-474e-a7c2-64efc87899f9` to
`f25a78f0-881f-4c2f-82ee-86e76dd19736` with no manual recovery or startup command.
BOOT v6 and the accepted module-compatible kernel were not modified.

## Owner folders and release closure

The new owner lacked standard Documents/Pictures folders. GNOME startup now runs
`xdg-user-dirs-update` as that owner, preserving custom paths and preferences.
The desktop package explicitly depends on `xdg-user-dirs` and `at-spi2-core`.
The exact-version release closure was rebuilt twice with identical outputs:

| Package | SHA256 |
| --- | --- |
| t630-desktop-runtime 0.1.2 all | b9536e95d16159ab7bffebc5d11037ecfe5df951f8ae3e072221ebc61d424e6d |
| t630-hardware-runtime 0.1.3 all | 09027ad06d32c8c31828a382b63754600c851074aef134e16ce36d4902ba5e50 |
| t630-release-base 0.1.10 arm64 | 0333bad3c3c49a92a992edb9aa2764efa7f64c6d0e4f110cefc2391f8a21ad70 |

All three installed/configured on the candidate, survived restart, and left
`dpkg --audit` empty. The updated assembler's read-only package validation then
checked all 14 staged release packages on-device for pinned hashes, package
names/versions, and private-stock-package permissions. Its temporary read-only
bind mount was removed afterward; no offline install or identity reset was run.
Existing Xournal++ autosave was copied without overwrite
to the owner's `Documents/T630-pen-test-before-restart.xopp` (46,332 bytes).
Compressed-file validation passed before restart and the file survived it;
app-level reopen acceptance is still pending. No handwriting is committed here.

## Unattended restart results

- Managed nested GNOME started with `--no-x11` and its normal password lock.
- The owner's wallpaper URI remained unchanged.
- Wi-Fi reconnected automatically around 80–83 seconds uptime.
- The bounded boot fallback started SSH and the screen service without a USB
  kick. The normal owner authenticated using the previously pinned host key.
- Root login and authentication with public keys disabled were rejected again
  after restart; direct LAN screen access remained refused.
- A fresh Mac-loopback SSH tunnel returned the physical PNG feed. Its black
  frame corresponded to the display service reporting `blanked: true`; the
  password lock was not bypassed or automatically unlocked.
- PipeWire's guarded speaker sink and microphone source were present.

This is successful **orderly restart**, not a full Power Off or return-to-stock
pass. A read-only outer diagnostic, `tools/show_ubuntu_mount_refs.sh`, reports
process references and nested mounts if teardown refuses unmount. Its exact
path boundary excludes sibling files such as `/run/ubuntu-start.log`.

## Wi-Fi delay cause and prepared probe

Kernel log: at 74.720056 seconds CNSS reported a 70000 ms calibration-completion
timeout; normal firmware/BDF initialization then ran around 75.8 seconds.
Samsung's downloaded SM-T630 Android 15 kernel source explains the ordering:

- `drivers/net/wireless/cnss2/pci.c`, `cnss_wlan_register_driver`: cold-boot
  calibration waits for `cal_complete` before registering wlan. Its comment
  requires the filesystem-ready trigger before qcacld loads.
- `main.c`, `fs_ready_store`: writing 1 posts `COLD_BOOT_CAL_START` when the
  device tree enables CBC; this is **not** a calibration-completion override.
- `cnss_cold_boot_cal_start_hdlr`: asserts if WLAN is already in mission mode.

Our current boot loads cnss2 and wlan consecutively without that normal trigger.
The exact platform exposes `fs_ready` and `qcom,wlan-cbc-enabled`. The DZE3 source
overlay archive's kernel update tar was inspected and contains no CNSS2 or other
wireless-source replacements; the cited base-source paths are unaffected by it.
Source archives were streamed, not unpacked into another large Mac directory.

`tools/signal_wifi_filesystem_ready.sh` defaults to read-only `--check`, pins
the model, kernel, selected root, exact platform and firmware prerequisites,
and refuses a loading/running wlan module. `--signal-ready` is an experimental
pre-wlan cold-start probe only. It supplies no invented MAC, changes no quirks
or regulatory settings, and writes no partition. It has **not** been enabled in
BOOT or physically tested for successful calibration. Its read-only check was
executed on the tablet and correctly refused the already loaded wlan module.
Do not invoke it as a repair after Wi-Fi is running.

## Pen diagnostics qualification

Mutter's missing stylus classification is established; loss of pressure is not.
GTK3 clones tool axes at client-specific proximity-in, making idle X/Y-only
enumeration inconclusive. Serial metadata now publishes after software-device
refresh so it targets the replacement device. Bounded 30-second live GTK tests
received no usable pen samples, so pressure remains unaccepted. The metadata
experiment is nonpersistent and was not automatically restored after restart.

See [pen acceptance](../PEN-APPS.md) and the
[preceding same-boot remote tests](clean-root-remote-pen-apps-20260915.md).

## Repository verification

The 247-test suite completed successfully (243 passes, four environment-dependent skips). This
includes package reproducibility/closure, metadata refresh ordering, active-pen
refusal, the diagnostic mount path boundary, and the default-read-only Wi-Fi
probe's live-driver gate. Successful pre-wlan calibration, physical pressure,
full Power Off, and return-to-stock remain unaccepted.
