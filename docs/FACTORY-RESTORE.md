# Full factory return

This is the recovery route for returning the development SM-T630 from the
Ubuntu/native-Android split layout to stock Samsung firmware. It erases both
operating systems and all user data. It does **not** relock the bootloader.

The only physically accepted baseline is the Wi-Fi `SM-T630`, XAR package
`T630XXSBDZE3`. Do not substitute SM-T636/SM-T638 firmware or remove the model,
PIT, hash, geometry, battery, and protected-neighbor checks.

## Accepted sequence

1. Deep-verify the complete four-file Samsung ZIP with
   `tools/verify_factory_firmware.py --deep --inventory`. The verifier requires
   the exact BL, AP, HOME_CSC, and CSC outer members and all 51 allowed inner
   entries.
2. Run `tools/prepare_factory_restore.py`. It checks the accepted ZIP SHA-256,
   repeats the deep verification, streams LZ4 decompression into a private new
   directory, and records hashes for the 40 flashable payloads. It selects the
   wiping `CSC`, never `HOME_CSC`.
3. Build Heimdall 2.2.2 from audited source. On Apple silicon, the accepted
   physical run used the two-point `LIBUSB_ERROR_PIPE` halt-clear patch from
   `aljosasavic/heimdall-apple-silicon` commit
   `df4daa54a016370b8ddbd9db8a01709cd09a03fb`.
4. If the tablet still has the project dual-boot split, boot the RAM-only
   maintenance image and run `maintenance/restore-stock-gpt` with the exact
   GPT backups created before and after the split. The helper proves the live
   table equals the saved split table, loads the original table, removes
   partition 35, restores full-size partition 34 `userdata`, exports and
   compares the result, and automatically reloads the split table on any
   incomplete transaction.
5. Enter Download Mode and run `tools/flash_factory_restore.py --payload-only`
   only after step 4 succeeds. The tool downloads and structurally compares the
   live 91-entry SM7325 PIT, then flashes exactly 40 Samsung payloads without
   `--skip-size-check`.
6. Leave the bootloader unlocked. Wait through the first stock boot and confirm
   the Samsung setup screen. A wiped device normally has no authorized ADB
   connection.

Heimdall's direct `--repartition` path was deliberately not retried after this
tablet rejected the PIT transfer before any partition upload. The accepted
recovery instead restored the exact pre-split GPT transactionally, then used a
normal payload session. This matters: merely flashing stock BOOT or AP files
does not remove the extra dual-boot partition.

Keep the original firmware ZIP, the deep-verification manifest, and the small
pre-split/post-split GPT backups. The decompressed restore directory is derived
data and may be removed after a verified factory boot.

See the [physical acceptance report](reports/full-factory-restore-20260917.md)
for hashes, refusal behavior, and the observed result.
