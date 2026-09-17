# Clean-install kernel correction — 2026-09-17

## Result

The explicitly authorized clean install completed against the existing split
layout. The installer formatted only p34 `linuxroot`, extracted the sealed
identity-clean Ubuntu root, verified the installed tree, and completed a clean
offline filesystem check. Android p35 was not formatted or mounted.

The first reboot found a release integration defect before owner setup. The
sealed dual-layout BOOT used the retired v13 Waydroid kernel, while the clean
root correctly contained the stock-assets package's module-compatible v12
modules. Kernel symbol-version checks therefore rejected `sec_tsp_log.ko` and
the dependent tablet startup path could not complete. The earlier development
root had hidden this mismatch because it still carried an incrementally staged
v13 module payload.

## Correction

Dual-layout Ubuntu BOOT v2 uses the physically proven v12 kernel with the same
restricted whole-disk/split-layout initramfs. Its exact properties are:

- BOOT SHA-256: `fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`
- kernel SHA-256: `7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6`
- size: 100,663,296 bytes
- accepted root: p34 `linuxroot`, 134,217,728 512-byte sectors

A recovery-console updater required the exact old BOOT, exact new BOOT,
model/build/kernel, partition identity and size, battery, and protected-neighbor
hashes. It wrote only p19 BOOT, re-read the complete partition, and reported
`DUAL_LAYOUT_BOOT_V2_WRITTEN_READBACK_VERIFIED`.

The subsequent reboot loaded the packaged touchscreen and WLAN modules and
reached the dark first-boot GNOME UI. The ownerless state remained intact:
there was no human account and `machine-id` was empty while the setup UI ran.

## Release hardening

- The dual-layout and maintenance builders now pin the module-compatible v12
  kernel and corrected Ubuntu BOOT.
- Maintenance v5 embeds BOOT v2 as its exact recovery image.
- Desktop 0.1.11 and release-base 0.1.20 pin the corrected Ubuntu switch hash.
- The private installer builder now requires a Magisk-patched Android BOOT,
  installs both switch images root-only, and seals their hashes in the rootfs
  manifest. It still refuses to create the Android-data acceptance marker;
  that marker requires physical encrypted-Android acceptance.
- The live clean root's restored private switch assets pass the complete
  read-only Ubuntu-side native-Android preflight.

The corrected identity-clean root was then cloned before owner creation,
audited, and archived. The final private root archive is 1,274,364,467 bytes,
contains 84,688 members, and has SHA-256
`7bbd12374677144ddcab7542c3f3dd6bd00dd33219ac604f069cb920e805bac1`.
Its manifest records desktop 0.1.11, release-base 0.1.20, the accepted rooted
Android BOOT hash, and Ubuntu BOOT v2. The complete six-input installer bundle
was sealed, immediately reverified against `SHA256SUMS`, and retained on p34;
the disposable 3.6 GB build clone was removed afterward.

That archive and bundle are retained above as the historical v2 correction
record. They are superseded by the owner-setup refresh below.

## Owner-setup refresh and sealed bundle v3

The completed owner walkthrough exposed three userspace issues without another
partition write:

- Wi-Fi association and DHCP had succeeded, but failure of a subsequent
  profile-hardening operation made the setup UI incorrectly blame the password.
  Association/DHCP is now the visible success boundary; the persistence step is
  best-effort and uses the exact client MAC from sysfs. The next physical boot
  reconnected `wlan0` automatically.
- The disposable first-boot GNOME host started the sensor client before audio.
  Both share ADSP, whose stock-kernel service publication is one-shot. First
  boot now registers the Qualcomm card, caches factory speaker calibration, and
  leaves the amplifiers off before it attaches sensors. A physical clean cold
  start then exposed `lahaina-yupikidp-snd-card`, created the normal 30% unmuted
  PipeWire speaker sink and microphone source, and restored GNOME volume policy.
- Google Chrome's ARM64 Wayland binary supports GNOME text-input-v3 but requires
  its explicit Wayland IME flag. Desktop 0.1.12 now derives an owner-private
  launcher from Chrome's current package-owned desktop file and adds only
  `--enable-wayland-ime --wayland-text-input-version=3`; Chrome updates remain
  package-owned and unmodified.

The refreshed exact set is first-boot 0.1.3, desktop 0.1.12, camera 0.1.7,
and release-base 0.1.21. Desktop 0.1.12 is reproducible at SHA-256
`3898ecbb797a11e41fe1e231e65752805b1bba232ddaabd7e71d0a25adde54a4`.
The live package database is clean and the ownerless source tree passed the
identity audit again before packaging.

Private root archive v3 is 1,274,356,982 bytes, contains 84,690 members, and
has SHA-256
`77ff0f3ffa8db7cf7c015a16e5df2bf0f22b72ff2dd9db82ab6973fdd23ac3bd`.
Its matching ARM64 installer runtime has SHA-256
`7218e2b2e87b9e55119e128e8ac68d492e223feef9710b1ed3da76aecdeb17f7`;
the accepted 100,663,296-byte BOOT remains
`fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`.
The six-input bundle was sealed and then independently reverified against its
generated `SHA256SUMS`. It remains private on p34 because it includes locally
reconstructed stock assets and both switch images. The superseded v2 bundle and
the disposable 3+ GB ownerless build tree were removed after verification,
leaving 56.6 GB free on `linuxroot`.

The initial Ubuntu-to-Android-to-Ubuntu touchscreen-button round trip passed but
did not catch Android's stale v1 return payload. The corrected v2 cycle described
below closes that generation mismatch; forced-failure coverage and the full
stock-recovery rehearsal remain.

## Post-v3 Chrome keyboard correction

Physical use showed that Chrome 153 negotiated `zwp_text_input_v3`, enabled its
text input, and committed the focused field, but nested Mutter did not convert
that protocol state into on-screen-keyboard visibility. The v3 launch flags
were therefore necessary but insufficient.

Desktop 0.1.13 keeps those flags, enables Chrome's renderer accessibility tree,
and adds an owner-session watcher limited to focused editable Chrome/Chromium
objects. It calls the same idempotent GNOME keyboard action already used by the
physical red button. A 400 ms AT-SPI collection check covers initial autofocus,
which can predate focus-event subscription, while normal text-input-v3 remains
responsible for closing the keyboard. The bridge does not inspect or log field
contents. Its reproducible package SHA-256 is
`ed7b3ad710cd2bfea1dbe28c971c8544704bfbf789977c420c03bbeaf50f29da`.
Release-base 0.1.22 locks that desktop package and has reproducible SHA-256
`84ce91801bb57479f9b54873c4eb4ffcb0a16fc44165b11f4d779d99186b2f46`.
The sealed v3 installer remains a valid historical artifact, but a replacement
bundle must not be declared until this bridge passes the real Chrome profile
and a clean restart.

The real owner Chrome profile then passed: a focused web field reached the
AT-SPI bridge, GNOME accepted `ShowKeyboard`, and the owner confirmed that the
keyboard opened automatically. A clean restart then restored Wi-Fi, the real
unmuted speaker sink, the watcher, and the Tablet Controls extension. Chrome
launched from the app drawer with all three managed flags and the keyboard was
visible again.

## Sealed bundle v4

The replacement bundle was rebuilt tablet-locally from the sealed v3 ownerless
archive rather than from the personalized running root. Only the fourteen
hash-pinned release packages were admitted; desktop 0.1.13 replaced 0.1.12 and
release-base 0.1.22 replaced 0.1.21. The resulting offline root passed the
identity audit, package audit, application inventory, native-linkage checks,
private dual-boot asset checks, and mount-leak gate before and after packaging.

Private root archive v4 is 1,274,375,145 bytes, contains 84,691 members, and has
SHA-256
`c7aea4fee23a8bd9661bd8da692b956f1f72aa41a079a8f78e9db863be46c1b8`.
Its ARM64 installer runtime remains byte-identical at SHA-256
`7218e2b2e87b9e55119e128e8ac68d492e223feef9710b1ed3da76aecdeb17f7`.
The accepted 100,663,296-byte BOOT remains
`fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`.
The root manifest declares no human account and no network credentials.

The six-input bundle was sealed and independently reverified against all seven
entries in `SHA256SUMS`. Every payload and control file is root-private mode
0600. No block device was opened or written during this refresh. The disposable
3.8 GB extracted root and 41 MB Mac transfer staging were removed only after the
seal passed; v3 remains available as a historical fallback. The tablet retained
55.3 GB free on `linuxroot` afterward.

During the handoff into this refresh the tablet had recently restarted. The
build had not begun, pstore contained no panic, the boot reason was normal, and
the retained Android kernel log recorded an orderly userspace
`sys.powerctl=reboot` rather than a watchdog or kernel panic. Because that
retained log may predate the immediately preceding Ubuntu boot, it is evidence
against a recorded Android crash, not proof of the exact trigger for the latest
restart.

The fresh v4-era cold-switch cycle subsequently exposed and corrected a stale
Android-side v1 Ubuntu payload. The corrected cycle returned on module-compatible
BOOT v2 and passed the complete Ubuntu health checks. Remaining release gates
are the untested forced-refusal classes and complete stock-recovery rehearsal.
