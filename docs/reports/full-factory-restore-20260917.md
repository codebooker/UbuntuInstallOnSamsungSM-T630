# Full factory restore acceptance — 2026-09-17

## Result

The development Wi-Fi SM-T630 was fully erased and returned from the installed
Ubuntu/native-Android split to Samsung XAR build `T630XXSBDZE3`. The original
single full-size `userdata` GPT layout was restored, all 40 available Samsung
firmware payloads completed, and the tablet rebooted and enumerated as normal
`SAMSUNG_Android` USB rather than the Ubuntu maintenance serial gadget.

The bootloader was intentionally left unlocked.

## Inputs

- Factory ZIP: `SAMFW.COM_SM-T630_XAR_T630XXSBDZE3_fac.zip`
- ZIP bytes: `6434873419`
- ZIP SHA-256:
  `24fd9cdf0a55ae3ae84b01b7b071dec845e90288a44b572767faaa20425876d5`
- Factory PIT SHA-256:
  `3c2eda15a7e01052b8c806f1c158f846c0783335494792341b74f9133b0578af`
- Pre-split GPT backup SHA-256:
  `242778fd0be1897e34cbf568ae4626917c8323a02aa2610212845486f74d5bb8`
- Post-split GPT backup SHA-256:
  `0d1cbbcd007cf924c59d70f0e29662711736267f863099c42783dd7d746f79ec`
- Audited Heimdall source commit:
  `df4daa54a016370b8ddbd9db8a01709cd09a03fb`
- Locally built arm64 Heimdall SHA-256:
  `cdacc24fa23ed3edfbeacd838552c194a66df9585b03b187ad7f7550fc093015`

The factory verifier passed ZIP CRC, Samsung appended MD5, and the exact
51-member inner allowlist before preparation. Every decompressed payload was
then hashed into a private restore manifest.

## Refusals and recovery

The first local preparation attempt refused before output because a manually
transcribed expected ZIP hash contained one incorrect character. A fresh live
SHA-256 and the saved deep manifest identified the transcription; no tablet
write occurred.

The initial Heimdall repartition attempt downloaded the live PIT successfully
but refused because the live 32 KiB PIT includes device firmware metadata while
the package PIT is 12,552 bytes. Their parsed 91-entry SM7325 partition
structures were identical. After accepting structural identity, Download Mode
rejected the PIT-transfer completion before any partition upload and rebooted.

The fallback used the exact GPT backups produced by the original split. Its
first maintenance attempt applied the stock table but encountered a stale
`/dev/sda19` node during the final protected-image check. The transaction trap
restored the split GPT. A fresh export matched the saved post-split GPT exactly.
The verifier was corrected to construct fresh block nodes from sysfs device
numbers. The second run restored the pre-split GPT, removed partition 35,
returned partition 34 to `userdata` sectors `21880832 + 226918360`, exported an
exact match to the pre-split backup, and rechecked all protected neighbors.

## Flash evidence

The final non-repartition session uploaded and received success acknowledgments
for 40 unique PIT targets: 25 BL payloads, 11 AP payloads, and 4 wiping CSC
payloads. The 8,868,571,396-byte sparse `SUPER` transfer and the
1,425,273,496-byte sparse `USERDATA` transfer both completed to 100%. Heimdall
then ended the session cleanly and requested a reboot.

After first-boot initialization, macOS observed Samsung vendor ID `0x04e8` and
Android product ID `0x6860` with product name `SAMSUNG_Android`. ADB listed no
authorized device, as expected after wiping userdata.

The owner then completed Samsung's normal setup and explicitly re-enabled USB
debugging for final verification. Android reported model `SM-T630`, device
`gtact4prowifi`, bootloader `T630XXSBDZE3`, and the exact stock release
fingerprint ending in `T630XXSBDZE3:user/release-keys`. Verified Boot reported
the deliberately retained unlocked/orange state. `/dev/block/by-name/userdata`
resolved to `sda34`; the `linuxroot` by-name entry and `sda35` were both absent.
This closes the physical factory-return gate through completed end-user setup,
not merely the first USB enumeration.

No serial number, credentials, calibration data, proprietary firmware, or GPT
backup is committed to the repository.
