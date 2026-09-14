# Guarded offline root assembly gate (2026-09-14)

## Result

`tools/assemble_release_root.py` now provides the fail-closed boundary between
the tested packages and a future generic Ubuntu root. In validation-only mode
it checks all ten exact package filenames, SHA256 values, Debian package names,
and versions. It also requires the proprietary stock package to remain
owner-only. The complete cache on the physical tablet passed this check.

Hardware runtime 0.1.2 now owns `/etc/t630-install-id` with the exact value
`SM-T630-T630XXSBDZE3-Ubuntu-v1`. The private stock package advanced to
1.0.1+dze3 and depends on that runtime; release-base 0.1.1 locks both revisions.
Native extraction confirmed the marker and both dependency contracts.

## Offline-root safety

The apply path refuses the live `/` root, symlinked roots, non-Ubuntu systems,
and roots without an explicit regular `.t630-offline-root` marker containing
`SM-T630 OFFLINE RELEASE ROOT`. Before installation it runs the release-root
audit that rejects human accounts, populated home directories, initialized
machine IDs, SSH host keys, root SSH state, saved NetworkManager/Netplan state,
and completed first-boot owner state.

Only an explicit `--apply --root PATH` runs offline `dpkg`. Component packages
are unpacked first, their configuration is completed inside that root, and the
exact-version metapackage is installed last. The device marker and identity
audit are checked again afterward. Validation is the default and performs no
root mutation.

## Remaining gate

The guard and package-directory audit are tested, but package installation into
a freshly downloaded and independently verified Ubuntu 24.04 ARM64 root has not
yet run. That disposable-root execution, first-boot provisioning, boot-image
assembly, and a full recovery rehearsal remain before any destructive installer
can be published.
