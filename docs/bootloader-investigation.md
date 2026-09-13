# SM-T630 bootloader investigation — 2026-09-12

## Direct observations

### Bootloader unlock confirmed

Post-wipe Wi-Fi reconnection verified: default network 100, KG `Checking`, bootloader `unlocked` / flash.locked=0, verified boot `orange`, warranty bit=0. Both earlier blockers are now cleared according to live Android properties. A working custom boot image and restore-tool compatibility remain to be established.

After the owner used Device Unlock Mode, live ADB returned: `ro.boot.flash.locked=0`, `ro.boot.vbmeta.device_state=unlocked`, `ro.boot.verifiedbootstate=orange`, `ro.boot.warranty_bit=0`, `knox.kg.state=Prenormal`, same build T630XXSBDZE3. Unlock is successful. Knox fuse remained zero, confirming earlier predictions of mandatory fuse tripping on unlock were incorrect. Need KG state to clear again before custom-image work.

- Stock package: `stock/SAMFW.COM_SM-T630_XAR_T630XXSBDZE3_fac.zip`.
- Prior MD5 check matched the distributor value. This checks consistency, not independently authenticated Samsung provenance or a tested restore path.
- Extracted BL archive and decompressed `abl.elf` without changing the source archive.
- Unpacked the embedded UEFI volume using `uefi_firmware`. Analysis workspace: `/tmp/t630-boot-audit.J5LCRu`.
- LinuxLoader PE (GUID f536d559-459f-48fa-8bbc-43b554ecae8d) contains DeviceLockUnlocking, GlibDrawDeviceUnlock, device_unlock.jpg, and OEM authorization routines. Their presence does not establish that the current policy permits invoking them.
- Disassembly at RVA 0x5b8c8 contains the DMC gate. At 0x5b964 it obtains DevAuthInfo and tests a 32-bit field at +0x138. The nonzero path prints `[Reboot Device - %a]` at 0x5b9c0 with `D2` as the argument (a reused suffix of the RSA-MD2 string at 0xf0c01). The exact semantics of the field have not been established.
- Nearby DMC routines communicate with the VaultKeeper trusted app. Do not equate this gate with the Knox Guard Prenormal state without further evidence.
- Live ADB became available during analysis. Tablet is booted into owner user 0, not Maintenance Mode user 77.
- Live values: `ro.boot.flash.locked=1`, `sys.oem_unlock_allowed=1`, `knox.kg.state=Prenormal`, `ro.boot.bootloader=T630XXSBDZE3`.
- LockSettings explicitly reports owner `CredentialType: PIN`, last changed 2026-09-11 23:51:10. Device-owner flag is false.

## Next diagnostic

### Wi-Fi reconnection result

After the owner connected Wi-Fi, direct ADB reports `knox.kg.state=Checking`, `ro.boot.flash.locked=1`, and `sys.oem_unlock_allowed=1`. Connectivity is validated. This transition occurred during this session without a seven-day wait. Next: cold hardware entry and inspect whether the Device Unlock menu is now offered. Android property is encouraging but Download Mode must confirm effective bootloader state.

### Follow-up: normal warning menu but no unlock option

- Removing the owner PIN cleared D2 for the user's hardware-button entry. The user reached a menu with Continue, Cancel, and Show barcode; no Device Unlock entry.
- Direct disassembly: 0x2fcfc invokes DMC screen gate, then 0x2fd00 calls policy function 0x4fa38. False selects `warning.jpg` via 0x28b60; true selects `warning_svb.jpg` via 0x28d40. At 0x2fd48 the same policy gates the long-press handler at 0x305b8 (argument 4000), which leads to the lock/unlock confirmation at 0x5bf20.
- Policy function 0x4fa38 consults OEM state, persistent OEM permission, KG state (+0x124 in DevAuthInfo), and an additional KG field (+0x12c). DevAuthInfo initializer 0x47ac8 populates +0x124 via `GetKGStatus` (0x565f8); confirmed by diagnostic string at 0xd8431. The lookup table at 0xd7248 contains 1,0,1,1,0,1 for states 0..5; nonzero blocks the handler in the relevant OEM-locked branch. No patch was made or flashed.
- Live ADB: user 0; bootloader locked; OEM allowed=1; KG Prenormal. Persistent data block raw diagnostic access is denied to shell.
- Knox service history unexpectedly reports Checking at 2026-09-12 00:16:35 with network connected, followed by Prenormal at subsequent boots (00:29 onward) with network disconnected. This is history, not a guarantee that reconnecting clears KG.
- Current connectivity service explicitly reports `Active default network: none`. Automatic date and time/time zone both enabled.
- Opened Wi-Fi settings via ADB to let the owner connect normally. Next step is observe KG service state after connectivity is restored. Do not issue fabricated broadcasts, modify KG state, or prescribe a timer based solely on the log.

PIN removal confirmed over live ADB at 2026-09-12 00:53:57 local: owner user 0, CredentialType NONE, SID zero. Bootloader remains locked, sys.oem_unlock_allowed=1, KG Prenormal. Cold hardware-button entry with no credential is the next pending test.

Remove the owner's screen PIN through Android Settings with the owner's authentication; observe whether the D2 gate changes on the next cold hardware-button entry. This is an experiment, not a verified fix for this build. It reduces physical-access protection and may remove enrolled biometrics. Do not collect the PIN in chat.

Samsung documents Auto Blocker as blocking USB commands/software installation; check its setting if needed: https://www.samsung.com/us/support/answer/ANS10003636/

## Corrections to previous advice

- ADB does not operate in Samsung Download Mode; an empty device list there is expected.
- Maintenance Mode entry does not itself unlock the bootloader or factory-reset the owner profile.
- sys.oem_unlock_allowed=1 alone is not proof the bootloader will accept an unlock.
- The earlier seven-day Samsung citation described Knox Guard enterprise activation, not this tablet's unlock timer. Magisk documentation separately describes 168h for Prenormal, but that does not establish the cause of D2 or guarantee resolution for this build: https://topjohnwu.github.io/Magisk/install.html
- Unlocking alone must not be assumed to trip the Knox warranty fuse. Custom software can trip it; observe status rather than prescribing a required value of 1.
- Native Ubuntu boot capability and a reliable restoration procedure remain unverified. No device partitions were modified in this investigation.
