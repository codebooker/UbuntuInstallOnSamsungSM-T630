# Dual-layout clean-installer gate (2026-09-17)

## Result

The physical SM-T630 produced and sealed a fresh private installer bundle for
the accepted Ubuntu/Android split layout. The ownerless Ubuntu 24.04 root is
3.5 GB, contains the complete `t630-release-base` 0.1.19 package closure, and
passes the identity, package, native-linkage, application, Waydroid-retirement,
and mount-leak gates. The archive contains no human account, initialized
machine identity, SSH host key, home data, or network credential.

The private rootfs archive is 1,230,453,239 bytes with 84,603 members and
SHA-256 `c3de265a819b17febc8b9b1209d3916e686d6121372bed869641ef07d3357d3a`.
The recovery runtime rebuilt byte-identically at SHA-256
`7218e2b2e87b9e55119e128e8ac68d492e223feef9710b1ed3da76aecdeb17f7`.
The sealed BOOT input is the physically accepted dual-layout Ubuntu image,
SHA-256 `eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb`,
not the retired pre-split v12 image. All private files remain mode 0600 and are
not redistributable.

## Split-layout correction

The first RAM-stage attempt exposed two stale single-OS assumptions and failed
closed before opening any block device:

- the installer still expected partition 34 to be the old 226,918,360-sector
  `userdata` extent;
- the bundle still pinned the old pre-split BOOT.

The corrected workflow targets only the 134,217,728-sector `linuxroot` at
`/dev/sda34`, separately verifies the 92,700,632-sector Android `userdata` at
`/dev/sda35`, and pins the installed dual-layout Ubuntu BOOT. Its one-time
authorization token now names `LINUXROOT`, so no UI or documentation suggests
that reinstalling Ubuntu should erase Android.

## Physical no-write acceptance

The complete final bundle was copied from mounted `linuxroot` into a bounded
`nosuid,nodev,noexec` recovery tmpfs. Every payload and seal checksum passed
before and after the copy. Check mode first returned the expected refusal while
Ubuntu was mounted:

```text
INSTALLER_REFUSED: linuxroot is mounted
```

A new recovery-side preparation helper then stopped only processes rooted in
the exact Ubuntu chroot, waited for graceful exit, detached child mounts
deepest-first without force or lazy unmounts, unmounted `linuxroot`, and kept
the RAM bundle intact. The final physical check reported:

```text
INSTALLER_PREPARE_COMPLETE_LINUXROOT_UNMOUNTED_RAM_PRESERVED
INSTALLER_CHECK_PASSED_LINUXROOT_UNMOUNTED_NO_DEVICE_WRITE
```

That pass reverified the exact model, kernel, split partition identities and
sizes, external power, accepted installed and bundled BOOT, untouched recovery,
vendor_boot, DTBO and VBMETA, all bundle hashes, and every isolated ARM64
recovery tool. No erase token was created, no filesystem was formatted, and no
block device was written.

## Remaining destructive acceptance

The bundle is staged and the device is at the explicit destructive boundary.
The next gate formats only `linuxroot`, extracts and validates the clean root,
runs read-only fsck, reboots into first-boot setup, and verifies that the new
owner flow plus both native OS switchers survive the clean installation.
Return-to-stock remains a separate final rehearsal.
