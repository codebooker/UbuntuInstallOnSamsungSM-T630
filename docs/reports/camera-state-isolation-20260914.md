# Account-neutral camera state (2026-09-14)

## Result

The stock DZE3 camera HAL does not require a prepared writable camera-data
image. A physical test replaced `/data` with a newly created empty hierarchy
containing only `vendor/camera`. The front camera then delivered eight 720×480
frames with measurable contrast (mean luma 108.25, standard deviation 97.55)
and created its own cache, custom-info, warm-start, configuration-dump, and
flash-state files.

The previously retained 72,173-byte `t630-s5k3l6-dv2-as-dv1.bin` was
byte-identical to the read-only stock vendor file
`com.samsung.sensormodule.0_lsi_s5k3l6_dv2.bin`; the empty-data test proved it
was an unused bring-up leftover. The two executable files found beside it were
also obsolete copies of helpers already owned by the redistributable package.
None is seeded into a fresh installation.

## Persistent path acceptance

Camera-runtime 0.1.3 creates root-owned
`/var/lib/t630-camera/android-data/vendor/camera` and bind-mounts that hierarchy
at `/data` only while the isolated Android compatibility runtime is active. It
does not depend on the installer-selected account name or home directory.

After a clean device restart, `/data` was initially unmounted. Starting the
rear camera mounted exactly
`/dev/sda34[/var/lib/t630-camera/android-data]` at `/data`, returned eight
frames, generated the missing rear flash-state file, and completed the bounded
camera teardown. The old per-user directory was not read or modified.

The upgraded camera package has SHA256
`7afd2321d075b56a605847606ed83790ea80169b179566200a38d782d908d619`.
The corresponding release-base 0.1.8 package has SHA256
`8f88105853441981198dec3c5c1acf215a73d715c89d41f1e131db6e4214cc0e`.
The preserved 3.1 GB clean release root accepted both upgrades and passed all
package, application, identity, native-linkage, camera-boundary, and mount-leak
checks.
