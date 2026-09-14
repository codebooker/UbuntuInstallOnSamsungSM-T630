# Guarded offline root assembly gate (2026-09-14)

## Result

`tools/assemble_release_root.py` now provides the fail-closed boundary between
the tested packages and a future generic Ubuntu root. In validation-only mode
it checks all fourteen exact package filenames, SHA256 values, Debian package
names, and versions. It also requires the proprietary stock package to remain
owner-only. The complete cache on the physical tablet passed this check.

Hardware runtime 0.1.2 now owns `/etc/t630-install-id` with the exact value
`SM-T630-T630XXSBDZE3-Ubuntu-v1`. The private stock package advanced to
1.0.1+dze3 and depends on that runtime; release-base 0.1.6 also locks the
account-neutral boot, PolicyKit, and login runtimes at 0.1.0.
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

## Fresh-root result

The guard subsequently installed the exact package set into a newly extracted,
identity-clean Ubuntu Base 24.04.5 ARM64 root on the physical tablet. Offline
configuration completed with no broken packages, no unresolved native-library
links, no leaked host mounts, and a clean post-install identity audit. A second
preserved clean root then accepted the Weston/Maliit boot runtime, including
repeat install and removal with byte-exact restoration of both diverted distro
files. The same root accepted the source-built PolicyKit agent, rejected a root
caller, accepted a same-owner non-root process subject, restored its diverted
D-Bus service exactly on removal, and passed final reinstall. See the
[fresh-root rehearsal](fresh-root-rehearsal-20260914.md).
The same root then accepted the reproducible GDM/elogind package, resolved all
four login-runtime ELF probes, restored the original PAM session file exactly
on removal, and passed repeat installation through the complete release set.
The camera runtime then passed the same removal/reinstall cycle: its files were
removed without affecting the desktop, hardware, or stock packages, and the
fourteen-file assembler restored it with a clean identity and package audit.

Boot-image assembly, a physical clean-boot walkthrough of the first-boot UI,
and a full recovery rehearsal remain before any destructive installer can be
published.
