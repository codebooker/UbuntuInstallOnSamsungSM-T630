# Release refusal and recovery gates — 2026-09-17

## Result

The physical SM-T630 passed the remaining non-destructive dual-boot refusal
drills and the read-only stock-recovery release gate. No partition was written,
no reboot was requested, and the running Ubuntu system remained healthy.

## Dual-boot refusal drills

`tools/check_native_android_switch_refusals.sh` runs the production
Ubuntu-to-Android helper only in its default `--check` mode. It uses a separate
mount namespace for each deliberate fault, makes the namespace private, and
bind-mounts a RAM file over exactly one input. The real root-owned artifacts and
block devices are never replaced.

The physical run verified these independent refusals:

- an incorrect accepted-Android image hash;
- a simulated `Discharging` battery state with no accepted external-power
  status; and
- a simulated recovery-partition hash mismatch.

Each case returned refusal status 1 with its expected reason. After every case,
the harness re-read BOOT, recovery, `vendor_boot`, DTBO, and VBMETA and required
all five pinned SHA-256 values. A final clean switch check passed. The terminal
result was `SWITCH_REFUSAL_GATES_PASSED_NO_PERSISTENT_CHANGES`.

## Exact factory package

The existing 6,434,873,419-byte DZE3/XAR factory ZIP passed
`tools/verify_factory_firmware.py --deep --inventory`. It contains exactly one
expected BL, AP, HOME_CSC, and CSC member. Streaming every member verified all
ZIP CRCs, Samsung-appended payload MD5 values, and trailer filenames without
extracting another multi-gigabyte copy.

The inner tar gate then required the exact safe allowlists and rejected path
traversal, links, device nodes, duplicates, missing payloads, and extras. The
physical package contains 26 BL, 13 AP, 5 HOME_CSC, and 7 CSC entries, including
the PIT and the complete BOOT/recovery/vendor_boot/DTBO/super/VBMETA/userdata/
modem/CSC recovery set. The mode-0600 JSON manifest remains private and outside
the repository. CRC and MD5 establish corruption resistance, not a Samsung
authenticity signature.

## Read-only stock-recovery gate

`tools/stage_stock_recovery_preflight.sh` now defaults to `--check`. Its only
write-capable path requires the explicit `--stage` argument; the check gate is
before the first `dd` in both source and tests.

The physical check used a private temporary mount namespace and a bounded
tmpfs over the Ubuntu root's `/tmp`. It supplied:

- the exact 2,048-byte non-wiping BCB;
- a host-saved 1,048,576-byte backup of `misc`;
- the matching host-verification marker; and
- the exact preflight authorization phrase.

The script validated the model, stock kernel, installation identity, split
partition geometry, unmounted Android data, battery and external power, GPT,
accepted BOOT, and the four protected neighbors. It returned
`STOCK_RECOVERY_PREFLIGHT_READY_NO_CHANGES`. The full `misc` hash was
`7c3277fd24046b110002c2a4f02fbbecfc4dedbd0ef1e5b39abe48c5128c9b17`
both before and after. BOOT remained
`fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`,
and all protected-neighbor hashes still matched.

The same physical check was repeated with no mode argument. It again returned
the read-only readiness result, and the complete `misc` hash remained exact,
proving the new default path rather than only the explicit `--check` alias.

The exact `misc` backup is retained off-device at mode 0600. The temporary BCB,
script, namespace, and tablet RAM files were discarded after verification.

## Remaining destructive boundary

A full Odin clean-stock restore would erase or replace the accepted dual-boot
installation. It is therefore not part of this non-destructive acceptance run.
The exact factory package, private manifest, Download Mode access, and `misc`
backup are ready for that final disaster-recovery rehearsal when destruction of
the current lab installation is explicitly intended. The bootloader must not be
relocked until all custom images have been replaced and stock Android has
booted successfully.
