#!/bin/sh
# Restore the accepted Ubuntu BOOT from a Mac/Linux host via Samsung Download Mode.
set -eu
export LC_ALL=C

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mode=${1:---check}
authorization=${2:-}
image=${T630_UBUNTU_BOOT_IMAGE:-$root/output/dual-layout-ubuntu-v2/boot.img}
bundled_heimdall=$root/output/heimdall-build/bin/heimdall
ubuntu_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f

fail() { echo "UBUNTU_DOWNLOAD_RESTORE_REFUSED: $*" >&2; exit 1; }
case "$mode" in
    --check|--write) ;;
    *) fail "usage: $0 --check | --write 'RESTORE ACCEPTED UBUNTU BOOT TO SM-T630'" ;;
esac

if test -n "${HEIMDALL_BIN:-}"; then
    heimdall=$HEIMDALL_BIN
elif test -x "$bundled_heimdall"; then
    heimdall=$bundled_heimdall
else
    heimdall=$(command -v heimdall || true)
fi
test -n "$heimdall" && test -x "$heimdall" || fail "Heimdall is unavailable"
test "$($heimdall version 2>/dev/null)" = v2.2.2 || fail "Heimdall 2.2.2 is required"
test -f "$image" && test ! -L "$image" || fail "accepted Ubuntu BOOT is absent or unsafe"
test "$(wc -c < "$image" | tr -d ' ')" = 100663296 || fail "Ubuntu BOOT size mismatch"
printf '%s  %s\n' "$ubuntu_boot" "$image" | shasum -a 256 -c - >/dev/null ||
    fail "Ubuntu BOOT hash mismatch"

if test "$mode" = --check; then
    echo UBUNTU_DOWNLOAD_RESTORE_LOCAL_ARTIFACTS_VERIFIED_NO_DEVICE_WRITE
    exit 0
fi
test "$authorization" = 'RESTORE ACCEPTED UBUNTU BOOT TO SM-T630' ||
    fail "authorization text mismatch"
$heimdall detect >/dev/null 2>&1 || fail "SM-T630 Download Mode device not detected"

work=$(mktemp -d "${TMPDIR:-/tmp}/t630-ubuntu-restore.XXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup 0 HUP INT TERM
pit=$work/current.pit
pit_text=$work/current-pit.txt

# Keep the same Heimdall session open after downloading the live PIT. The flash
# resumes only after the live table proves the exact BOOT identifier and size.
$heimdall download-pit --output "$pit" --no-reboot >/dev/null
$heimdall print-pit --file "$pit" >"$pit_text"
awk '
    /^--- Entry #[0-9]+ ---$/ { in_entry=0; id=""; count="" }
    /^Identifier: 19$/ { id="19" }
    /^Partition Block Count: 24576$/ { count="24576" }
    /^Partition Name: BOOT$/ { if (id == "19" && count == "24576") found=1 }
    END { exit found ? 0 : 1 }
' "$pit_text" || fail "live PIT BOOT identity or 96 MiB size mismatch"

$heimdall flash --BOOT "$image" --resume
echo UBUNTU_BOOT_FLASH_SENT_BY_HEIMDALL_VERIFY_FULL_HASH_AFTER_UBUNTU_RETURNS
