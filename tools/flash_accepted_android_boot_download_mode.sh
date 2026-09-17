#!/bin/sh
# Flash one locally accepted Android BOOT through the live SM-T630 PIT.
set -eu
export LC_ALL=C

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mode=${1:---check}
authorization=${2:-}
image=${T630_ANDROID_BOOT_IMAGE:-$root/output/private-t630-magisk-boot.img}
expected=${T630_ANDROID_BOOT_SHA256:-}
bundled_heimdall=$root/output/heimdall-build/bin/heimdall

fail() { echo "ANDROID_DOWNLOAD_FLASH_REFUSED: $*" >&2; exit 1; }
case "$mode" in
    --check|--write) ;;
    *) fail "usage: $0 --check | --write 'FLASH ACCEPTED ANDROID BOOT TO SM-T630'" ;;
esac
case "$expected" in
    ''|*[!0-9a-f]*) fail "accepted Android BOOT hash is absent or malformed" ;;
    *) ;;
esac
test "${#expected}" = 64 || fail "accepted Android BOOT hash length mismatch"

if test -n "${HEIMDALL_BIN:-}"; then
    heimdall=$HEIMDALL_BIN
elif test -x "$bundled_heimdall"; then
    heimdall=$bundled_heimdall
else
    heimdall=$(command -v heimdall || true)
fi
test -n "$heimdall" && test -x "$heimdall" || fail "Heimdall is unavailable"
test "$($heimdall version 2>/dev/null)" = v2.2.2 || fail "Heimdall 2.2.2 is required"
test -f "$image" && test ! -L "$image" || fail "accepted Android BOOT is absent or unsafe"
test "$(wc -c < "$image" | tr -d ' ')" = 100663296 || fail "Android BOOT size mismatch"
printf '%s  %s\n' "$expected" "$image" | shasum -a 256 -c - >/dev/null ||
    fail "Android BOOT hash mismatch"

if test "$mode" = --check; then
    echo ANDROID_DOWNLOAD_FLASH_LOCAL_ARTIFACT_VERIFIED_NO_DEVICE_WRITE
    exit 0
fi
test "$authorization" = 'FLASH ACCEPTED ANDROID BOOT TO SM-T630' ||
    fail "authorization text mismatch"
$heimdall detect >/dev/null 2>&1 || fail "SM-T630 Download Mode device not detected"

work=$(mktemp -d "${TMPDIR:-/tmp}/t630-android-flash.XXXXXX")
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
echo ANDROID_BOOT_FLASH_SENT_VERIFY_EXACT_HASH_AFTER_ANDROID_RETURNS
