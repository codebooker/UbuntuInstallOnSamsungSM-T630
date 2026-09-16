# Full private installer bundle and read-only device gate (2026-09-16)

## Result

The physical SM-T630 produced and sealed the first complete ownerless installer
bundle without copying the multi-gigabyte root filesystem to the Mac. The build
used the exact `T630XXSBDZE3` stock-assets boundary and the fourteen pinned
release packages under `t630-release-base` 0.1.15.

The fresh Ubuntu 24.04.5 ARM64 root was 3.5 GB and passed the identity audit,
`dpkg --audit`, `apt-get check`, native linkage checks, and the mount-leak gate.
It contains no human account, home data, network connection, initialized
machine ID, or SSH host identity. GNOME Settings, GNOME Software, native Mozilla
Firefox, LibreOffice, Xournal++, and MyPaint are present before first boot.

The sealed private inputs were:

| Input | Bytes | SHA256 |
| --- | ---: | --- |
| `t630-release-rootfs.tar.gz` | 1,230,162,230 | `a8788b2068b3f624a7d93600ef530da12bf5155301ff39c939a511f0f3da6b1d` |
| `t630-installer-runtime.tar.gz` | 2,066,455 | `7218e2b2e87b9e55119e128e8ac68d492e223feef9710b1ed3da76aecdeb17f7` |
| accepted v12 `boot.img` | 100,663,296 | `a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28` |

The root archive has 84,589 members and was serialized with numeric ownership,
ACLs, xattrs, sorted paths, a fixed timestamp, and timestamp-free gzip output.
Its private manifest and the bundle seal both declare the proprietary boundary.

## Physical RAM staging

`stage_installer_bundle_local.py` verified the seal on mounted userdata, checked
model, kernel, userdata geometry, battery, and available memory, mounted a
bounded `nosuid,nodev,noexec` tmpfs, copied the complete bundle into it, and
verified all seven checksum entries again. It reported:

```text
INSTALLER_BUNDLE_COPIED_FROM_USERDATA_TO_RAM_NO_DEVICE_WRITE
```

The working GNOME processes were then stopped, every userdata child mount was
detached, and `/dev/sda34` was genuinely unmounted. The guarded installer
verified the exact userdata partition, accepted installed BOOT, stock recovery,
vendor_boot, DTBO, VBMETA, external power, and every isolated ARM64 recovery
tool. It reported:

```text
INSTALLER_CHECK_PASSED_USERDATA_UNMOUNTED_NO_DEVICE_WRITE
```

No authorization token was created, no filesystem was formatted, and no block
device was written. The existing userdata filesystem was remounted and the
tablet cold-started back into the personalized root. GNOME and Weston returned,
Wi-Fi obtained its saved address, package checks were clean, the bundle remained
present on userdata, and the checked kernel fault-marker count was zero.

## Bugs found by the fresh build

The package apply exposed that the public dependency recipe did not explicitly
request `gnome-control-center`, even though the desktop package requires it and
the documentation said Settings was included. The provisioner and checker now
name that package directly. They also name the physically accepted Xournal++
and MyPaint packages so a clean installation matches the tested tablet rather
than requiring a later manual app install.

## Remaining destructive gates

The separate typed authorization path has not been invoked. A full userdata
format, archive extraction, normal end-user first boot, and stock-return
rehearsal remain intentionally distinct destructive acceptance gates.
