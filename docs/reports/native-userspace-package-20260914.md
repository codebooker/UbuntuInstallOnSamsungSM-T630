# Reproducible ARM64 native userspace package (2026-09-14)

## Result

Six small compatibility artifacts were rebuilt twice from repository source on
the physical Ubuntu ARM64 tablet. The builds used fixed locale/time metadata,
path-prefix normalization, and disabled linker build IDs. Every corresponding
artifact was byte-identical between the two independent output directories.

Build hashes:

| Artifact | SHA256 |
| --- | --- |
| `im-t630-wayland.so` | `d9956901fabb8301996e097ac7b33223134aab08f4f941a8a638117d80b0fe80` |
| `t630-capture` | `16331b38283e0756fa81af736c5eb64e99f1ebb5be2cc23289e3cc33e8454a99` |
| `t630-cogl-sync.so` | `6f541e352f0b5fa78d562cf45468164aa9b77c23117af76f9c4b1e93a4d31492` |
| `t630-drm-compat.so` | `4a6db8019d7fa1ab7afcdcfa86c220a816311c129166420c80ea8a5265a0e77c` |
| `t630-rotation.so` | `e831528b45891786b6b92cfbaab8580d05122753eb559c0cad534c64501e2c24` |
| `t630-xput-image.so` | `63a2b4f97244229b5a2700a2468aecb214595dc41fe222407589501c2fa52e92` |

`tools/build_native_userspace_deb.py` validates each input as a regular,
non-symlinked, little-endian ELF64 AArch64 shared/PIE artifact before packaging.
Two package builds were byte-identical:

- name: `t630-native-userspace_0.1.0_arm64.deb`
- size: 28,920 bytes
- SHA256: `b6e9dffc3ce27278084a0fbc9022189e289eaf3c06fdcc5db1e9877a6dfed6ff`

The package contains those six binaries, an owned empty GTK module-cache path,
and the project copyright file. Its target-only post-install action regenerates
that cache with Ubuntu's fixed ARM64 GTK query tool. It has no pre-install
script, partition operation, firmware, Android library, account, home directory,
owner marker, credential, or network profile.

## Native validation

The package was copied to the tablet and parsed and extracted by native arm64
`dpkg-deb`; it was not installed over mapped live libraries. All six files were
executable ELF64 AArch64 objects and resolved through `ldd`. The exact declared
runtime packages were present on Ubuntu 24.04:

- `libc6`
- `libdrm2`
- `libgtk-3-0t64`
- `libwayland-client0`
- `libweston-13-0`
- `libxcb1`

Additional isolated probes loaded the Cogl, DRM, and XPutImage libraries into a
no-op process; registered the extracted GTK input module with
`gtk-query-immodules-3.0`; found `wet_module_init` in the Weston module; and
verified the capture executable returns usage failure for an invalid argument.
All passed. No active compositor, GNOME, input, display, or library mapping was
replaced during validation.

## Remaining boundary

Patched GDM/elogind, the policy agent, sensor adapter, camera/video helpers,
Bluetooth service, audio integration, and stock-derived firmware are outside
this package. They require their own reproducible packages or a local
non-redistributable asset generator before generic-root assembly can be called
complete.
