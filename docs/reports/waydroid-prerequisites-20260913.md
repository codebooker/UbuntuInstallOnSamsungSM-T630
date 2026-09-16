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
Further ABI isolation invalidated the boot-image-only plan. A build adding only
`CONFIG_PID_NS` changed 157 of the 417 kernel symbol CRCs imported by the stock
WCN6850 Wi-Fi module. A complete audit compared all modules in the installed
vendor module tree against that build: all 235 modules were affected. The
universal `module_layout` change alone prevents safely mixing those Samsung
modules with the modified kernel; major drivers also contain many additional
symbol mismatches.

The stock module payload must never be force-loaded and its CRCs must never be
patched. The historical v9 writer now fails closed.

## Exact Qualcomm WLAN source and first coherent external build

The public manifest for Qualcomm release
`LA.UM.9.14.r1-19400-LAHAINA.QSSI13.0` identifies the same
`2.0.8.28B` WLAN driver family found in the DZE3 stock module. It pins three
CodeLinaro repositories:

- `qcacld-3.0` at `4e15799e1f443577a9a102bc0c9564259e502b03`;
- `qca-wifi-host-cmn` at `0904701ee8ae065bbc920c7d5a2a11c0c645ebaa`;
- `fw-api` at `2b58351f875928929af63aa548fa0b84f3050587`.

The initial checkout had accidentally used the qcacld revision for
`qca-wifi-host-cmn`; using the manifest's independent host-common revision
restored the expected QDF headers. The exact source then compiled and linked
with Clang LTO against the full Waydroid-capable kernel configuration.

An additional Android-kernel build trap was found during the ABI audit. This
5.4 build's external-module `modpost` reads both `Module.symvers` and any
`vmlinux` left in the output directory. A stale diagnostic `vmlinux` silently
overrode the correct full-build CRCs despite an exact `vermagic`. The new WLAN
builder temporarily hides that file, treats the completed `Module.symvers` as
the sole ABI authority, restores `vmlinux` on every exit, and then runs a
read-only ELF audit. The audit tool parses `.ko` sections directly; unlike
`objcopy --dump-section` without an output path, it cannot rewrite the input
module while inspecting it.

The resulting stripped private module is 14,755,144 bytes with SHA-256
`ed4f8bbe62a83e8b3935fe330e5588fdc34a5c63008dc2686e49b22757432060`.
It reports the exact release
`5.4.274-qgki-31225846-abT630XXSBDZE3`, the same four CNSS dependencies as the
stock module, and 477 imported symbols. All 477 exist in the full Waydroid
kernel's `Module.symvers`, and all 477 CRCs match. Relative to the original
stock WLAN module, 477 imports are common, 229 retain the same CRC, 248 differ
as expected for the new kernel ABI, and the stock module alone imports
`cnss_sysfs_get_pm_info`, `cnss_sysfs_update_driver_status`, and `kmemdup`.

At this point this was an offline feasibility artifact, not a module installed
on the tablet. The remaining gate was a complete coherent replacement payload
for every module required at boot, followed by a guarded native Ubuntu
regression boot.

## Physical v13 and Android acceptance (2026-09-16)

The closure work subsequently produced 99 required external modules. The final
v13 image preserves the exact stock release string, and the audit matched all
13,709 imported symbol CRCs. The staged BOOT image has SHA-256
`1403afb30d584418ea6bfc011317f33bf8073294eae355d0c05d8d61c7355e76`;
its kernel payload has SHA-256
`49b648801a751be9761bd8b2b24e9833964acbb06741d87f7db384dd2d36845d`.
It completed the guarded native regression sequence before Android userspace
was installed.

Waydroid 1.6.2 now boots the official ARM64 VANILLA LineageOS 20 / Android 13
images to `sys.boot_completed=1`. Because Ubuntu itself is a chroot below the
recovery-hosted root, the first ordinary LXC start leaked inherited trace
descriptors named below `/run/ubuntu`; Android's zygote rejected them. The
packaged outer-root/private-mount-namespace launcher fixes that boundary while
leaving LXC's own pivot unchanged. The stable `system_server` trace descriptors
resolve to `/sys/kernel/tracing/trace_marker`, the LXC monitor root is `/`, and
the nested GNOME session uses `t630-gnome-0`.

Android networking and orderly container teardown pass. F-Droid 1.23.2 was
installed from its canonical site, persisted across a clean session restart,
and launches through its generated GNOME app-grid entry. No Google services or
Google account were installed. The reproducible device integration is packaged
as `t630-waydroid-runtime` 0.1.6; external Waydroid packages and Android images
remain an optional post-install boundary documented in [WAYDROID.md](../WAYDROID.md).

Primary references:

- [Waydroid overview and namespace model](https://docs.waydro.id/)
- [Waydroid Ubuntu installation](https://docs.waydro.id/usage/install-on-desktops)
- [Tab S9 Ultra Waydroid validation](https://github.com/agcarbajo/ubuntu-galaxy-tab-s9-ultra/blob/bb55ceb87b61db7629c0820101ce7884ff8d987b/docs/waydroid.md)
- [CodeLinaro qcacld-3.0 source](https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qcacld-3.0)
- [CodeLinaro qca-wifi-host-cmn source](https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qca-wifi-host-cmn)
- [CodeLinaro fw-api source](https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/fw-api)
