# Local installer and recovery gates (2026-09-16)

## Result

The release now has a single host-side command that creates the two private
inputs needed by a future recovery-hosted installer: an identity-clean Ubuntu
rootfs archive and the accepted persistent BOOT image. The command performs no
device I/O and cannot authorize a write.

`tools/build_local_installer.sh` requires root on ARM64 Linux, a pinned Ubuntu
Base archive, the complete exact package directory, the accepted
module-compatible kernel, and a new work directory. It runs the existing
preparer, public dependency provisioner, fail-closed package assembler, full
rehearsal checker, new rootfs archive builder, BOOT builder, and final identity
audit in that order.

## Rootfs archive boundary

`tools/build_release_archive.py` accepts only a marked Ubuntu 24.04 offline
root that still passes the identity audit, has the exact installation marker,
and records every package locked by `t630-release-base` 0.1.15 as installed at
the expected version. It refuses existing output or temporary paths.

The archive is built by GNU tar with numeric ownership, ACLs, all xattrs, one
filesystem, sorted paths, fixed timestamps, and deterministic gzip headers. It
and its manifest are mode 0600. The manifest states that the archive contains
locally reconstructed proprietary stock assets and must not be redistributed.
It also records the archive SHA256, byte and member counts, exact package
versions, and clean identity/network state. The source root is audited again
after the archive is read. A final sealer pins the BOOT input to the exact v12
hash and accepted module-compatible kernel, validates both manifests against
their payloads, and writes a private bundle manifest plus
BusyBox-compatible `SHA256SUMS`. This gives the recovery transport one small,
unambiguous pre-format verification file.

Thirteen new unit tests cover complete version state, stale versions,
human-account and live-mount rejection, exact recovery roles, deep trailer
verification, corrupt MD5 data, missing roles, nested ZIP members, the host-only
workflow, one-time sealing, modified rootfs rejection, and unaccepted BOOT
rejection.

## Stock recovery boundary

`tools/verify_factory_firmware.py` validates exactly one DZE3/XAR BL, AP,
HOME_CSC, and CSC tar archive inside the owner's factory ZIP. The default pass
reads only ZIP metadata so it does not create another multi-gigabyte copy. Its
opt-in deep pass streams all data and validates both ZIP CRCs and Samsung's
appended tar MD5/trailer names without extraction.

CRC and MD5 checks establish corruption resistance, not publisher
authenticity. The full Samsung package remains private and must be retained
outside the install host. A physical Odin clean-stock restore remains an
acceptance gate, and the bootloader must not be relocked while any custom image
remains.

The owner's 6,434,873,419-byte
`SAMFW.COM_SM-T630_XAR_T630XXSBDZE3_fac.zip` completed the deep pass. All four
members reported `deep_verified: true`; their ZIP CRCs, appended payload MD5s,
and trailer filenames matched. The tool streamed the existing archive and
wrote only a small private JSON report below the ignored `reports/` directory.

## Remaining installer boundary

The host artifact construction is now explicit and fail-closed. The missing
piece is a recovery-hosted USB transport that receives the whole private
archive, verifies its manifest and SHA256 before formatting, targets only the
exact validated userdata partition, extracts ownership/ACLs/xattrs, validates
the resulting root, and writes BOOT only after root installation succeeds.
That destructive stage is not implied by the new build command.
