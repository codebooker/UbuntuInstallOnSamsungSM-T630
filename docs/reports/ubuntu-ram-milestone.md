# Ubuntu userspace milestone — 2026-09-12

**Ubuntu 24.04.5 ARM64 userspace executes natively on the tablet's Samsung
5.4.274 kernel.** It is a chroot in RAM under `/run/ubuntu`, not an Android
container, not a VM, not yet a systemd-as-PID-1 boot, and not a desktop install.
PID 1 remains the previously flashed BusyBox diagnostic init.

## Verified source and transfer

- Official archive: ubuntu-base-24.04.5-base-arm64.tar.gz from
  https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/
- Archive size: 29936675 bytes.
- SHA256: a91d5a93010193712d346d761372b7c9db6dfcf093893161c64ca107f05914f2.
- Detached SHA256SUMS signature verified against Ubuntu's documented full
  CD Image signing-key fingerprint 843938DF228D22F7B3742BC0D94AA3F0EFE21092.
  Verification used PGPy; its unimplemented revocation/self-signature checks
  emitted warnings. The key fingerprint was pinned to Ubuntu's HTTPS
  documentation, not trusted merely from a keyserver result.
- Transfer via raw USB serial: 1-MiB rehearsal succeeded, then the full archive
  transferred in 1.6 seconds and matched SHA256 on the tablet before extraction.
- Archive extracted only under tmpfs-backed `/run/ubuntu`.

## Actual execution

`ubuntu-native-first-run.txt` records successful execution of:

- Ubuntu Bash 5.2.21 (aarch64).
- Ubuntu glibc 2.39-0ubuntu8.8.
- dpkg architecture arm64 and apt package version 2.8.3.
- base-files 13ubuntu10.5 and Ubuntu 24.04.5 release metadata.

At initial preflight, the device had 5361 MiB usable RAM, about 5143 MiB
available, battery 20%, Charging, and battery temperature 28.0 C. `/run` had
2.6 GiB capacity, about 132 MiB used after extracting Ubuntu plus keeping the
compressed archive. No internal block-device filesystem was mounted.

## Display query and first mode-setting test

- Kernel DRM driver is **msm_drm**, version 1.4.0 (20130625), not mainline `msm`.
- Ubuntu's current libdrm 2.4.125-1ubuntu0.1~24.04.2 tools were installed into
  the RAM-only Ubuntu tree. All six package checksums were checked against
  Ubuntu Packages indexes whose checksums matched InRelease. That InRelease
  signature was verified by native Ubuntu gpgv against its archive keyring:
  F6ECB3762474EDA9D21B7022871920D1991BC93C, Ubuntu Archive Signing Key (2018).
- `/dev` was bind-mounted into `/run/ubuntu/dev`. This exposes device nodes;
  it is not an internal filesystem mount. No disk node was opened for writing.
- `modetest -D /dev/dri/card0` failed because it treated the argument as a bus ID.
  `modetest -M msm` also failed. **Use `modetest -M msm_drm`.**
- Query succeeded: connector **55 DSI-1**, encoder 54, CRTC **113**, preferred
  mode index **0**, `1200x1920x60x159772vidNS`, 60 Hz. The panel is portrait in
  native scanout despite typical landscape use. Do not use Virtual-1's modes.
- A 20-second temporary test ran:
  `modetest -M msm_drm -s '55@113:#0'` in Ubuntu. It reported setting the
  advertised mode and exited 0. The owner confirmed: "showed the test pattern
  for a while now is black". Visible scanout is therefore confirmed, not just
  inferred from ioctl success. Kernel logs show panel shutdown on test exit, so a blank screen
  after those 20 seconds is expected and does not mean the system stopped.
- The read-only query is saved in drm-readonly-probe.txt; mode test output is
  in display-pattern-test.txt. This is not proof of GPU acceleration or touch.

## State and next work

- No new flash, repartition, internal root filesystem installation or disk wipe
  happened during this milestone. The previously flashed BOOT/VBMETA remain.
- RAM Ubuntu and these added packages disappear when the tablet restarts.
  The boot image will still start the diagnostic system, not this Ubuntu tree.
- USB diagnostic serial remains the management path:
  `/dev/cu.usbmodemT630BRINGUP0011` on the Mac.
- `serial_link.py` runs authored shell scripts and copies their output, or
  transfers exact byte counts into /run with SHA256 checking. Its raw upload
  receiver restores terminal settings after a 90-second timeout if transfer
  fails. Do not blindly repeat uploads: it refuses to overwrite existing paths.
- Next milestones: software-rendered graphical
  session; obtain/load exact stock touchscreen and pen modules; networking;
  then design persistent rootfs and PID1 boot. No hardware support should be
  marked working without measured evidence.
