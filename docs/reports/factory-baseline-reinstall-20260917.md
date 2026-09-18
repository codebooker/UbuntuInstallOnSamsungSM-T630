# Factory-baseline Ubuntu reinstall (2026-09-17)

The physical SM-T630 completed a second Ubuntu installation starting from the
fully restored, wiped `T630XXSBDZE3`/XAR factory layout. This is materially
different from the earlier clean-root rehearsal, which began with the
dual-boot partition table already present.

## Stock-origin split

The guarded stock-origin maintenance operation required the exact model,
build, kernel, factory partition geometry, power state, protected partition
hashes, host-verified complete GPT backup, and an explicit destructive token.
It shrank only the already-wiped stock `userdata` extent into:

- p34 `linuxroot`: 134,217,728 sectors (64 GiB);
- p35 `userdata`: 92,700,632 sectors (about 44.2 GiB).

Neither new partition was formatted by the split operation. The exact original
GPT was retained off-device for recovery.

## Ubuntu installation

The private installer was staged entirely in RAM and passed all seven sealed
checksums. Its read-only gate accepted the verified factory VBMETA as well as
the previously accepted Ubuntu-era VBMETA, while still pinning every other
protected image and the complete split geometry. Apply formatted only p34 as
ext4 UUID `64de8544-53ea-4fdc-8946-d6b07e238630`; p35 remained blank and
unmounted.

Independent post-install checks confirmed the installation marker, empty
machine identity, absence of human accounts and network credentials, exact
embedded Android and Ubuntu switch images, clean read-only ext4 check, valid
GPT, and exact accepted Ubuntu BOOT readback. The installed system reached the
dark owner-creation UI with touch and GNOME running.

## Final private bundle

Bundle v5 contains `t630-desktop-runtime` 0.1.14 and `t630-release-base`
0.1.23. Its root archive is 1,124,514,888 bytes with SHA256
`0d0ecadcd605c0b926cbb4ebd2273494acb10e7ac66616718f7befad235b5b05`.
Every seal entry verifies, and the repository suite passes 535 tests with four
intentional skips.

After the owner installed Chrome in the already-running first session, the
one-shot launcher integration had already run and Chrome opened without its
Wayland/accessibility flags. Desktop 0.1.15 adds an owner-session watcher that
idempotently regenerates the private launcher when Chrome is installed or
updated later; release-base 0.1.24 pins that correction for bundle v6. A Chrome
153 follow-up found that an already-running background process could still
ignore the regenerated launcher and that the unqualified accessibility switch
could expose only empty AT-SPI frames. Desktop 0.1.16 uses Chrome's explicit
`on-screen` accessibility mode and retires incompatible background processes;
release-base 0.1.25 pins that correction for the next sealed bundle.
Bundle v6 then passed the complete clean-root build and seven-entry seal. Its
1,124,525,634-byte root archive has SHA256
`c226a6afa266c34713bf7de106d70ba94e8137374706cb0d52bce70b5537e728`;
the expanded repository suite passes 543 tests with four intentional skips.
Bundle v7 repeats the complete Ubuntu Base build with desktop 0.1.16 and
release-base 0.1.25. Its 1,124,532,229-byte root archive has SHA256
`0ba5af631964cb96006b38bb54cadcc2f1c1bf0c856ab7eb9a708df3aa693053`;
all seven published checksums and all six payload manifest records verify. The
repository suite passed 544 tests with four intentional skips. Physical launch
from GNOME's cached pre-correction desktop entry then exposed a regression: the
watcher retired the incompatible Chrome process but did not replace it, so the
tap appeared to do nothing.

Desktop 0.1.17 turns that retirement into an atomic compatibility replacement:
it terminates only the owner's incompatible Chrome main process, waits for it
to exit, and launches Chrome with the required Wayland IME, text-input-v3, and
explicit on-screen accessibility flags. The exact stale-launch path was
reproduced on the tablet; the watcher replaced it with a compatible process,
AT-SPI exposed the editable address bar, and GNOME reported the on-screen
keyboard visible. Bundle v8 pins this fix with release-base 0.1.26. Its
1,124,529,333-byte root archive has SHA256
`e13d6391bebe3f5c4ce32cf41a19397f2912e4a0c7525712785711681bc080f9`;
all seven published checksums and all six independently recomputed payload
size/hash records verify. The repository suite passes 545 tests with four
intentional skips.

## Remaining physical gate

Stock recovery must initialize only p35 and Android encryption metadata, after
which Android first boot and the command-free Android-to-Ubuntu return are
repeated. Complete pre-initialization `misc` and `metadata` backups have been
saved off-device and SHA256 verified. Ubuntu p34 and all protected neighbors
remain outside the recovery staging write set.
