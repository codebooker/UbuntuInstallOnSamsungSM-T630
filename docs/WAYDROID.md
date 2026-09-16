# Android applications with Waydroid

Waydroid is experimentally working on the physical SM-T630. The verified
combination is Waydroid 1.6.2, LXC 5.0.3, and the official ARM64 VANILLA
LineageOS 20 / Android 13 images on the v13 kernel/module payload. Android
reaches `sys.boot_completed=1`, networking works, and F-Droid launches from the
GNOME app grid and survives a clean Android restart.

This is an optional post-install feature. It is not yet in the sealed offline
native base because the Waydroid Ubuntu packages come from Waydroid's external
repository and the Android system/vendor images are downloaded separately. Do
not add `t630-waydroid-runtime` to `t630-release-base` until those inputs have a
reproducible installer boundary.

## Why this port needs a launcher

Ubuntu runs from a filesystem mounted below `/run/ubuntu` by the retained
recovery host. Starting LXC directly from that chroot leaves inherited Android
trace descriptors named `/run/ubuntu/sys/...` after LXC pivots into the Android
root. Android 13's zygote rejects that inconsistent filesystem view and
`system_server` exits.

`ubuntu/t630-waydroid-lxc-start` enters PID 1's outer mount/root namespace,
creates a private mount namespace, recursively exposes the Ubuntu runtime, and
then executes the distro LXC binary unchanged. The recursion is required
because `/proc`, `/dev`, `/sys`, and `/run` are nested mounts. With the wrapper,
`system_server` owns canonical `/sys/kernel/tracing/trace_marker` descriptors
and remains stable.

The integration package also:

- mounts only the fixed cgroup-v1 controllers required by this 5.4 kernel;
- creates binder, hwbinder, and vndbinder devices through binderfs;
- prepares a lightweight container coordinator during desktop startup while
  leaving Android stopped until the owner launches an Android app;
- selects the account-neutral nested GNOME socket rather than assuming a user
  name or Wayland display; and
- gives the guarded Ubuntu shutdown path explicit Waydroid, cgroup, and
  binderfs teardown.

## Install on a provisioned tablet

First boot the exact v13 kernel and matching module payload. Never combine the
Waydroid kernel with the old Samsung module tree or force-load a module with a
mismatched ABI. The kernel build and guarded staging path are documented in
[the prerequisite report](reports/waydroid-prerequisites-20260913.md).

Follow Waydroid's official Ubuntu instructions to add its repository, then
install the exact tested host versions:

```sh
sudo apt install waydroid=1.6.2 lxc=1:5.0.3-2ubuntu7.2
```

Build and install this repository's integration package:

```sh
SOURCE_DATE_EPOCH=1700000000 python3 tools/build_waydroid_runtime_deb.py
sudo apt install ./output/t630-waydroid-runtime_0.1.4_all.deb
```

That exact reproducible build has SHA-256
`03159705fd8eb221ccaed67c1d1e8d6a36eb248b7ec07dd5e926ac6695ed4bdd`.

Initialize the official ARM64 VANILLA image. This downloads roughly 2.4 GB of
system and vendor image data and does not include Google services:

```sh
sudo waydroid init -s VANILLA
sudo t630-waydroid-prepare
```

The normal desktop startup runs the preparation helper on later boots. It can
be disabled without removing data by creating `/etc/t630/waydroid.disabled`.

Launch the full Android UI as the account created by first boot:

```sh
waydroid show-full-ui
```

Android applications installed by Waydroid receive `.desktop` launchers in
that owner's app grid. The wrapper resolves the owner and runtime directory at
execution time; no lab user name or fixed home path is packaged.

## F-Droid

The physical acceptance run installed the canonical `F-Droid.apk` from
`https://f-droid.org/F-Droid.apk`. The tested file was F-Droid 1.23.2,
versionCode 1023052, SHA-256
`985f5181d48bb6bafd54083a048b391271e0ab28385881cc41294fb01a222762`.
That digest describes the 2026-09-16 acceptance artifact; verify a newer
download against F-Droid's current official publication rather than assuming
the old digest will remain current.

Install a verified APK as the desktop owner:

```sh
waydroid app install /absolute/path/to/F-Droid.apk
```

## Validation

After launching Android, these checks should all pass:

```sh
waydroid status
sudo waydroid shell getprop sys.boot_completed
sudo waydroid shell pm list packages org.fdroid.fdroid
```

Expected status is a running session and container on
`WAYLAND_DISPLAY=t630-gnome-0`; boot completion is `1`; and the final command
prints `package:org.fdroid.fdroid`. A host-side diagnostic may additionally
confirm that the LXC monitor's root is `/` and that every `system_server`
trace-marker descriptor resolves below `/sys/kernel/tracing`, never
`/run/ubuntu`.

Clean Restart and Power Off are part of the integration test. Do not unmount
the Ubuntu root while Waydroid's container is running. The packaged guarded
shutdown requests a normal container stop, waits for LXC to report `STOPPED`,
and refuses the host unmount if any Android mount remains busy.

## Current limitations

- This uses the VANILLA image. Google Play services and account setup were not
  installed or tested.
- Host/Android clipboard sharing is not enabled. A preliminary bridge could
  not access the locked GNOME clipboard reliably and was removed.
- Android applications still need longer rotation, suspend/resume, camera,
  audio, and touch/S Pen acceptance passes.
- Waydroid packages and images are not yet cached in the private offline
  installer bundle, so an initial network connection is required.

Primary references are Waydroid's
[Ubuntu installation guide](https://docs.waydro.id/usage/install-on-desktops),
the [Waydroid documentation](https://docs.waydro.id/), and the
[Tab S9 Ultra project that inspired this work](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/blob/bb55ceb87b61db7629c0820101ce7884ff8d987b/docs/waydroid.md).
