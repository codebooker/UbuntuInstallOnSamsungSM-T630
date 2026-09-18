#!/bin/sh
# Flash only the pinned RAM maintenance BOOT through the live SM-T630 PIT.
set -eu
export LC_ALL=C

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mode=${1:---check}
authorization=${2:-}
image=$root/output/dualboot-maintenance-v5/boot.img
expected=c45e960fcbc6a30ab98872529d27a157a41409ea7601166330956b7f6e74ea4e
bundled_heimdall=$root/output/heimdall-build/bin/heimdall

fail() { echo "MAINTENANCE_DOWNLOAD_FLASH_REFUSED: $*" >&2; exit 1; }
case "$mode" in
    --check|--write) ;;
    *) fail "usage: $0 --check | --write 'FLASH RAM MAINTENANCE BOOT TO SM-T630'" ;;
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
test -f "$image" && test ! -L "$image" || fail "maintenance BOOT is absent or unsafe"
test "$(wc -c < "$image" | tr -d ' ')" = 100663296 || fail "maintenance BOOT size mismatch"
printf '%s  %s\n' "$expected" "$image" | shasum -a 256 -c - >/dev/null ||
    fail "maintenance BOOT hash mismatch"

if test "$mode" = --check; then
    echo MAINTENANCE_DOWNLOAD_FLASH_LOCAL_ARTIFACT_VERIFIED_NO_DEVICE_WRITE
    exit 0
fi
test "$authorization" = 'FLASH RAM MAINTENANCE BOOT TO SM-T630' ||
    fail "authorization text mismatch"
$heimdall detect >/dev/null 2>&1 || fail "SM-T630 Download Mode device not detected"

work=$(mktemp -d "${TMPDIR:-/tmp}/t630-maintenance-flash.XXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup 0 HUP INT TERM
pit=$work/current.pit
pit_text=$work/current-pit.txt

$heimdall download-pit --output "$pit" --no-reboot >/dev/null
$heimdall print-pit --file "$pit" >"$pit_text"
awk '
    /^--- Entry #[0-9]+ ---$/ { id=""; count="" }
    /^Identifier: 19$/ { id="19" }
    /^Partition Block Count: 24576$/ { count="24576" }
    /^Partition Name: BOOT$/ { if (id == "19" && count == "24576") found=1 }
    END { exit found ? 0 : 1 }
' "$pit_text" || fail "live PIT BOOT identity or 96 MiB size mismatch"

$heimdall flash --BOOT "$image" --resume
echo MAINTENANCE_BOOT_FLASH_SENT_VERIFY_CONSOLE_BEFORE_STORAGE_WORK
