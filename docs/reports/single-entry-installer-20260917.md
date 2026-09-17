# Single-entry installer coordinator — 2026-09-17

## Result

`tools/t630_installer.py` is now the single host-side entry point for the
already accepted installer components. It does not contain partition paths,
format commands, or an apply implementation. It delegates each phase to the
existing narrowly tested verifier, RAM stager, orderly preparation helper, and
typed authorization tool.

The default tablet-local invocation verifies the complete bundle, copies it
from mounted `linuxroot` into bounded tablet tmpfs, uploads the guarded
installer, and stops. It cannot format or write a partition. Optional phases
are explicit:

- `--verify-only` checks a host-side bundle without connecting to the tablet;
- `--prepare` stops only the exact Ubuntu chroot, unmounts `linuxroot`, and runs
  the final read-only device gate;
- `--staged` resumes an already verified RAM bundle without recopying it; and
- `--install` is rejected without `--acknowledge-stock-recovery`, then delegates
  to the existing tool that still requires the exact typed
  `ERASE SM-T630 LINUXROOT` phrase and a fresh tablet-side check.

The physical default path copied sealed bundle v4 from `linuxroot` into RAM,
verified every entry against `SHA256SUMS` before and after the copy, and returned
`INSTALL_ASSISTANT_COMPLETE: bundle staged in RAM; no device write`. The tmpfs
was then unmounted and removed. BOOT remained
`fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f`
and `misc` remained
`7c3277fd24046b110002c2a4f02fbbecfc4dedbd0ef1e5b39abe48c5128c9b17`.

## Button-driven host window

`tools/t630_installer_gui.py` provides **Verify**, **Stage**, **Prepare
(read-only)**, and **Install Ubuntu** buttons over the coordinator. It can browse
for a host bundle, accept a tablet-local bundle path, or resume a bundle already
staged in RAM. It runs the coordinator with an argument vector and never invokes
a shell. The GUI itself contains no block-device path, format operation, or
apply implementation.

The Install button additionally requires the recovery checkbox, the exact erase
phrase in the window, and a final destructive confirmation. Only then does it
feed that same phrase to the existing authorizer, which repeats the tablet-side
gate. The window refuses to close while a guarded phase is active, including
the short process-start interval.

This closes the command-fragmentation and basic graphical-wrapper gaps. A signed
standalone host application is still future packaging work. The Ubuntu
first-boot experience itself is already touch-first and physically accepted
with user-selected language, network, account, password, time zone, and privacy
settings.
