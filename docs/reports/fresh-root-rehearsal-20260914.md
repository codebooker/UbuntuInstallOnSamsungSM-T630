# Fresh Ubuntu release-root rehearsal (2026-09-14)

## Result

The first complete, non-destructive release-root rehearsal passed on the
physical SM-T630. It used a new directory on the tablet's userdata filesystem;
the working live root was neither replaced nor modified by the package apply.

The input was Canonical's `ubuntu-base-24.04.5-base-arm64.tar.gz`, previously
verified against Ubuntu's signed checksum list and pinned here at SHA256
`a91d5a93010193712d346d761372b7c9db6dfcf093893161c64ca107f05914f2`.
`tools/prepare_rehearsal_root.py` verified that digest, checked 3,413 archive
paths for traversal, extracted into a new dedicated directory, installed the
offline marker, and passed the identity audit.

## Public dependencies and identity handling

`tools/provision_rehearsal_root.sh` mounted only the temporary device, proc,
sysfs, and resolver views required for package configuration. Its
`policy-rc.d` denied service startup inside the chroot. It installed the public
Ubuntu dependencies for GNOME, NetworkManager, its explicit `wpasupplicant`
Wi-Fi backend, PipeWire, BlueZ, sensors,
Weston, Xwayland, GTK, and the native helpers. The expanded run also installed
GNOME Software/PackageKit, Firefox, LibreOffice, Files, Terminal, Text Editor,
Contacts, media codecs, and the normal GNOME utilities.

The first run found a real release-image problem: systemd/DBus package setup
generated `/etc/machine-id` and `/var/lib/dbus/machine-id`. The provisioner now
empties/removes build-time machine identity and the random seed after package
configuration, so each installed device creates its own identity at first boot.
The corrected run passed the release audit.

## Exact package apply and acceptance

The initial guarded assembler pass verified and installed the ten-file DZE3
release set. A second preserved clean root subsequently accepted the expanded
twelve-file set, adding the packaged Weston/Maliit host and PolicyKit runtimes.
A later pass accepted the fourteen-file set and added the isolated GDM/elogind
login runtime plus the redistributable camera runtime. The camera package's
five helpers were checked as ARM64 ELF files, while a negative scan confirmed
that no private Android image, camera calibration, or mutable state entered the
clean root. The preserved root then accepted camera-runtime 0.1.4 and
release-base 0.1.9; its full package, application, identity, linkage, and mount
audit remained clean.
Acceptance recorded:

- all fourteen exact package versions in `installed` state;
- empty `dpkg --audit` output;
- exact `/etc/t630-install-id` value;
- no unresolved libraries for `t630-capture`, the Weston rotation module,
  Weston, Maliit, the PolicyKit agent, elogind, GDM, or its session worker;
- no temporary host mounts left below the rehearsal root;
- clean post-install identity audit;
- 3.1 GB expanded root size after public dependencies, applications, and device packages;
- unchanged healthy live GNOME, Wi-Fi, Bluetooth, audio, battery, and sensor
  services, with zero kernel-fault markers.

Firefox came from Mozilla's native ARM64 APT repository at version
`155.0.1~build1`. The provisioner verified the repository key's pinned SHA256
and fingerprint before enabling it. APT policy gave that package priority 1000,
assigned Ubuntu's `1:1snap1` transition package priority -1, and did not install
`snapd`. Package archives and temporary GnuPG state were removed after the
install while repository indexes and AppStream metadata were retained for the
first GNOME Software launch.

## First-boot backend

The packaged backend then ran with the repository's deliberately non-personal
sample profile and a throwaway test password. It created an active UID/GID 1000
account, assigned the available `sudo`, `audio`, `video`, `plugdev`, `input`,
`render`, and `t630-owner` groups, and applied the requested hostname, locale,
keyboard, and time zone. The packaged desktop autostart `--check` resolved that
new owner successfully. Running the backend a second time was refused.

As a final negative check, the release audit rejected the personalized root for
its owner marker, non-secret setup profile, populated home, and human account.
That is expected: only an unpersonalized root may become a distributable image.

## Remaining boundary

This proves clean-root assembly, reversible host-runtime installation, and
account-backend execution, not bootability. Next are boot-artifact assembly, a physical clean-boot UI walkthrough, and a
destructive boot/recovery rehearsal. The proprietary DZE3 package remains
owner-only on the tablet and is not part of the repository.
