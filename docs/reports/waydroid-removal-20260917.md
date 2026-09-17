# Waydroid removal — 2026-09-17

Native Android's physical button-only round trip superseded the CPU-rendered
Waydroid experiment. Waydroid was stopped with no active mounts before removal.

The development tablet then removed:

- `waydroid` 1.6.2 and `t630-waydroid-runtime` 0.1.7;
- the system image, writable container state, and per-owner application data;
- generated Android application launchers;
- preserved Waydroid backups and obsolete kernel/module trial artifacts;
- the retired package repository/key and SM-T630 Waydroid startup helpers; and
- the GNOME-only Waydroid fullscreen hook and desktop startup preparation path.

The accepted Ubuntu BOOT, active stock module set, native Android partitions,
and both button switchers were deliberately outside the removal set. Package
health, GNOME startup, and the native Android switch preflight were rechecked
after cleanup.

The source and chronological Waydroid reports remain in Git as historical
bring-up evidence. Fresh release roots never depended on the optional external
Waydroid repository, and desktop runtime 0.1.10 removes its last dormant hooks.
