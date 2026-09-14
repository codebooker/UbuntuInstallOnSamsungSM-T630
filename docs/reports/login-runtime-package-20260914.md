# Reproducible login runtime package (2026-09-14)

## Result

`tools/build_t630_login_runtime.sh` now builds the authentication/session
components that had previously existed only as a working development install:

- package: `t630-login-runtime_0.1.0_arm64.deb`
- size: 1,804,420 bytes
- SHA256: `edfc0b58325acc95c1e4dd25befd53bdaec30faf795dfb8a37d06fb4de6aa23e`

Two complete builds on the ARM64 tablet were byte-identical. The builder stages
its output and never installs over the running tablet.

## Pinned source and isolation

The package builds elogind `v255.27` and Ubuntu GDM
`46.2-1ubuntu1~24.04.9` from hash-checked public source archives. GDM includes
Ubuntu's complete patch series plus `ubuntu/gdm-auth-only-greeter.patch`. Both
projects install below versioned `/opt/t630` prefixes. The GDM binary uses an
RPATH to the private elogind library, so the host's systemd/logind files are not
replaced.

The private GDM configuration disables its local greeter, XDMCP, and remote
login. It supplies only the verifier used by GNOME's standard lock screen. The
private elogind configuration ignores power and suspend actions; the tested
T630 power helper retains exclusive control of the tablet's guarded sleep path.

The package creates no account and contains no password or device identity.
Empty `login.enabled` and `lock-on-start` markers activate the managed session
only after first boot has created the installer-selected owner.

## Clean-root acceptance

Ubuntu's unmodified `gdm3` package was first installed in the identity-clean
rehearsal root to provide its system account, PAM profiles, and public runtime
dependencies without starting services. The T630 package then installed and
passed:

- empty `dpkg --audit` output;
- linkage checks for elogind, `pam_elogind.so`, GDM, and the GDM session worker;
- exact safe private configuration checks;
- release identity/privacy audit;
- complete removal, byte-exact restoration of the original
  `/etc/pam.d/common-session`, and clean reinstall;
- repeat installation through the guarded thirteen-file release assembler;
- no temporary mount leaks.

The same source revisions, T630 patch, private configuration, and launchers had
already passed physical password rejection, correct-password unlock, power-key
lock/wake, and the delayed touch-keyboard fix on the development tablet. The
new package closes that reproducibility gap; a first boot from the clean root is
still required before the complete image is called end-user ready.
