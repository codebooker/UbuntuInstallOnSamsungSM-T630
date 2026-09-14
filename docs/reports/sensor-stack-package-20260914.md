# Reproducible sensor stack packages (2026-09-14)

## Result

`tools/build_t630_sensor_stack.sh` now performs a native Ubuntu ARM64 build
from four pinned and SHA256-verified archives. It builds the same three-package
boundary used by the working development tablet:

| Package | Size | SHA256 |
| --- | ---: | --- |
| `libssc_0.4.4-t6303_arm64.deb` | 64,876 bytes | `22f8ab83a5799efe44bb4873eb89ab0a7b9e20c908bd42ee917c3fe42acf3807` |
| `hexagonrpcd_0.4.0-t6303_arm64.deb` | 24,486 bytes | `0b97140e1b803f0362da17b5e1bf1ed96295f68accd04fffdc00d15c4ffd2db9` |
| `iio-sensor-proxy_3.9-t6303_arm64.deb` | 43,574 bytes | `1ffcc6881cf458e400d2efac744ba38564415a1f416e4c2ed9ef37fa0354bd29` |

Two clean builds in the same declared build root were byte-identical for all
three packages. The source inputs are libssc 0.4.4, hexagonrpc 0.4.0,
iio-sensor-proxy 3.9, and the exact S9 Ultra reference revision
`bb55ceb87b61db7629c0820101ce7884ff8d987b`. The builder records and checks the
archive digest for each before extraction, and no longer depends on an
untracked `/work/reference-s9-ultra` checkout. Its default build tool is Meson
1.7.2 in a temporary virtual environment, installed from a hash-pinned wheel;
an explicitly supplied Meson must be version 1.4 or newer.

## SM-T630 changes

The build applies the reference project's registry-write, rename, listener
buffer, synchronous-wait, and early-claim fixes. It then applies this
repository's downstream FastRPC subsystem patch and selects the SM-T630 stock
`auto_brightness` SSC stream. Source paths and package versions are explicit,
and linker-cache maintenance is included for the two packages that install
shared libraries.

## Native validation

The packages were built on the physical tablet without installing over the
known-working t6302 stack. Native `dpkg-deb` metadata parsing and extraction
passed. All principal files reported AArch64 ELF headers, the extracted sensor
proxy resolved the extracted `libssc.so.2` without a missing dependency, and
the isolated `--help` load probes for the sensor proxy and FastRPC daemon
completed. The trees contain no `/home`, `/opt/t630`, Python bytecode cache,
Samsung firmware, sensor registry, account state, network credential, or
device identity.

## Remaining boundary

The working services still require the device's matching Qualcomm firmware and
Samsung sensor registry/configuration files. Those are not redistributable and
must be generated locally from the exact stock firmware by the future
`t630-stock-assets` package builder. These packages were deliberately not
installed over the live stack merely to test packaging; full installation is a
fresh-root rehearsal gate.
