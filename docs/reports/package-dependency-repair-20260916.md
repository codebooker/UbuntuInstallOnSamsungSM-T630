# Package dependency repair and reboot acceptance (2026-09-16)

## Result

The installed SM-T630 root now has a coherent Debian package graph. Before this
repair, `apt-get check` rejected four component relationships left behind by
incremental development: boot runtime required hardware 0.1.2, camera required
desktop 0.1.1 and hardware 0.1.2, login required desktop 0.1.1, and stock assets
required hardware 0.1.2. The corresponding live packages had already moved
forward.

Component dependencies now express the oldest compatible package version with
`>=`. The dependency-only `t630-release-base` package remains the release lock
and pins every component with `=`. This lets an individual component be upgraded
without making APT inconsistent while still preventing a release root from
silently mixing untested revisions.

The accepted set is:

| Package | Version | SHA256 |
| --- | --- | --- |
| `t630-desktop-runtime` | 0.1.5 | `d78c7934aa120f407a84db30b545128f1080a7f1c50ccb4a986fdf42428ec8c4` |
| `t630-hardware-runtime` | 0.1.6 | `a0864399a0211e474128f1b84529e1dd2a47a0417b526193bbb2bd77bb59c02b` |
| `t630-boot-runtime` | 0.1.1 | `1aee3360ebcfd4bbb014d69f04a4d4381538fadc3b3c10346c1e0bdd9e2aba90` |
| `t630-login-runtime` | 0.1.2 | `173be4723fc419c6a87f1d9e922831c87cae6b168c2fbe8ee62672deec98dd20` |
| `t630-camera-runtime` | 0.1.5 | `23693c00b83b4a3b5edef9c4d47c108d48065d7868a0065a70555db102a8c585` |
| `t630-stock-assets` | 1.0.2+dze3 | `7bfa16d266592116bddae1c2a23c607585802a1e9b2c05905bc97e25210f0efe` |
| `t630-release-base` | 0.1.14 | `7ae9ee1cd6ebaaa207fe4f71afa8d925b2a9f809be00aa641f75f015a2349d3f` |

The stock-assets archive was built and installed only on the tablet. It contains
Samsung/Qualcomm material and was not copied to the host, uploaded, or committed.

## Login builder repair

The native ARM64 login builder now declares `dconf-cli`, uses a checksum-gated
download cache, and gives GDM build-only `libelogind.pc` metadata pointing into
the staging tree. The packaged metadata still points to
`/opt/t630/elogind-255.27`; no temporary build path is shipped. Its
Debian-policy `copyright` file also remains present in the minimal root, whose
dpkg configuration intentionally excludes other files below `/usr/share/doc`.
Two consecutive builds with `SOURCE_DATE_EPOCH=1700000000` produced the same
package hash shown above.

## Physical acceptance

The refreshed dependency set was installed in order and the tablet was rebooted
normally. After restart:

- `dpkg --audit` produced no output and `apt-get check` succeeded.
- Weston, managed GNOME, the login guard, touch, and the S Pen started.
- Wi-Fi associated with the configured network and owner-only SSH plus HTTPS
  became reachable.
- GNOME reported the calibrated speaker sink and built-in microphone source.
- Sensor proxy reported an accelerometer, the password lock was active, and the
  minimize/maximize/close layout remained selected.
- The checked kernel log contained no new fault marker.

The filesystem-ready Wi-Fi path was also preserved: readiness was accepted at
3.77 seconds and WLAN module loading returned at 20.85 seconds, without the old
70-second startup timeout.

The final login 0.1.2 archive changes only packaging metadata relative to the
accepted runtime: its license material is consolidated into the path retained
by the minimal root. It and release-base 0.1.14 were then installed on that
running system. `dpkg --verify t630-login-runtime` was silent, APT remained
clean, the managed GNOME session and login guard remained active, and both
transfer files were removed.

## Automated acceptance

The package-specific unit set passed 24 tests. The complete repository suite
then passed 326 tests with five intentional skips.
