# Waydroid prerequisite investigation (2026-09-13)

The Tab S9 Ultra reference project uses Waydroid 1.6.2 with an official ARM64-
only LineageOS 20 / Android 13 GAPPS image. Its main device-specific repair was
shipping the Netfilter modules required by `waydroid-net.sh`; it does not reuse
Samsung's installed Android userspace as the container image.

The SM-T630's current DZE3 kernel already has binderfs with binder, hwbinder and
vndbinder devices, ashmem, overlayfs, namespaces generally, cgroups, veth,
bridge, IPv4 connection tracking/NAT/iptables/MASQUERADE, seccomp, and the
Netfilter owner match. The exact live-config check found six missing runtime
features plus the System V IPC dependency required for an IPC namespace:

- PID, IPC, and user namespaces;
- System V IPC, on which this 5.4 kernel's IPC namespace depends;
- cgroup PID and device controllers;
- the Xtables CHECKSUM target used for Waydroid DHCP replies.

Patch `0009-enable-waydroid-container-support.patch` makes only those configuration
changes and the required IPC dependency. `check_waydroid_kernel.py` provides a
repeatable read-only gate, and `build_waydroid_kernel.sh` verifies the matching
Samsung source before applying the complete device patch series.

The Samsung archive contains filenames that differ only by letter case,
including `xt_MARK.h` and `xt_mark.h`. Extracting it onto the default
case-insensitive macOS filesystem silently merges those headers and produces a
misleading Netfilter compiler failure. The builder now detects that condition;
source extraction and compilation must happen on a case-sensitive Linux
filesystem (a Linux container volume is sufficient).

## First kernel and module build

The first Waydroid-capable Image was packed into the existing tested ramdisk.
The resulting custom boot image has SHA-256
`57b5d0c8a1ef76f46ea0c6c039d30a2f13e7b3743c5c7d1a72eb5f4eb10a993b`.
Its kernel payload has SHA-256
`59924b824a651c0f9b9ce61c255a6b40a96c936aea69d3607fb0414f0311a297`.
The guarded writer verified the current boot image and every protected adjacent
partition, wrote only `BOOT`, and verified its full readback. The tablet then
booted the expected release and all Waydroid configuration checks passed.

Changing namespace and cgroup options changed the module-version ABI. Startup
therefore stopped safely when the first stock external touch module was
rejected; old modules were not force-loaded. A clean Linux-filesystem rebuild
now completes the Image and 99 unique external modules with GCC 13. The clean
build produced Image SHA-256
`588c7d719d11c7b51b4df0509a4e2b9b29586b1faf7d8f46ea2da167ba6cdb67`
and `Module.symvers` SHA-256
`92306e5f2b025198a5e28ed2a76449c42089f6a88796cf42c7b99c8bffc98296`.
Runtime module replacement and the complete desktop regression pass are the
next physical gate. No Waydroid image or Google account has been installed yet.

Primary references:

- [Waydroid overview and namespace model](https://docs.waydro.id/)
- [Waydroid Ubuntu installation](https://docs.waydro.id/usage/install-on-desktops)
- [Tab S9 Ultra Waydroid validation](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/blob/bb55ceb87b61db7629c0820101ce7884ff8d987b/docs/waydroid.md)
