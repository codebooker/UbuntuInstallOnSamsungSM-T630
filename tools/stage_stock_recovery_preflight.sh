#!/bin/sh
# Schedule one non-wiping stock-recovery boot through the standard misc BCB.
set -eu
export LC_ALL=C

mode=${1:---check}
case "$mode" in
    --check|--stage) ;;
    *) echo "usage: $0 --check|--stage" >&2; exit 2 ;;
esac

candidate=/tmp/t630-recovery-preflight-bcb.bin
backup=/tmp/t630-misc-before-recovery.bin
host_marker=/tmp/HOST-VERIFIED-MISC-BACKUP
authorization=/tmp/AUTHORIZE-STOCK-RECOVERY-PREFLIGHT
misc=/dev/sda10
bcb_hash=b0b0993da05a79506348c702de750e300e866532b20a6024c2e85aa5350e0957
misc_hash=7c3277fd24046b110002c2a4f02fbbecfc4dedbd0ef1e5b39abe48c5128c9b17

fail() { echo "STOCK_RECOVERY_PREFLIGHT_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1
    device=$2
    label=$3
    printf '%s  %s\n' "$expected" "$device" | sha256sum -c - >/dev/null ||
        fail "$label hash mismatch"
}
tail_hash() {
    dd if="$1" bs=2048 skip=1 status=none | sha256sum | awk '{print $1}'
}

test "$(id -u)" = 0 || fail "root is required"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline || fail "model mismatch"
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3 ||
    fail "kernel baseline mismatch"
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1 ||
    fail "Ubuntu installation mismatch"
grep -qx PARTNAME=misc /sys/class/block/sda10/uevent || fail "misc identity mismatch"
test "$(cat /sys/class/block/sda10/start)" = 203096 || fail "misc start mismatch"
test "$(cat /sys/class/block/sda10/size)" = 2048 || fail "misc size mismatch"
grep -qx PARTNAME=linuxroot /sys/class/block/sda34/uevent || fail "linuxroot identity mismatch"
test "$(cat /sys/class/block/sda34/size)" = 134217728 || fail "linuxroot size mismatch"
grep -qx PARTNAME=userdata /sys/class/block/sda35/uevent || fail "userdata identity mismatch"
test "$(cat /sys/class/block/sda35/size)" = 92700632 || fail "userdata size mismatch"
test -z "$(ls /sys/class/block/sda35/holders)" || fail "userdata has holders"
major_minor=$(cat /sys/class/block/sda35/dev)
if awk -v wanted="$major_minor" '$3 == wanted { found=1 } END { exit found ? 0 : 1 }' \
        /proc/self/mountinfo; then
    fail "userdata is mounted"
fi
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 50 ||
    fail "battery below 50 percent"
status=$(cat /sys/class/power_supply/battery/status)
case "$status" in
    Charging) ;;
    Full)
        ac=$(cat /sys/class/power_supply/ac/online 2>/dev/null || echo 0)
        usb=$(cat /sys/class/power_supply/usb/online 2>/dev/null || echo 0)
        test "$ac" = 1 || test "$usb" = 1 || fail "external power is required"
        ;;
    *) fail "external power is required" ;;
esac

check_hash fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f /dev/sda19 boot
check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 recovery
check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 vendor_boot
check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 dtbo
check_hash a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 vbmeta
sgdisk --verify /dev/sda >/tmp/t630-gpt-before-recovery.txt 2>&1 || fail "GPT verification failed"
grep -q 'No problems found' /tmp/t630-gpt-before-recovery.txt || fail "GPT problems reported"

for path in "$candidate" "$backup" "$host_marker" "$authorization"; do
    test -f "$path" && test ! -L "$path" || fail "$path is absent or unsafe"
    test "$(stat -c %u "$path")" = 0 || fail "$path is not root-owned"
done
test "$(stat -c %s "$candidate")" = 2048 || fail "BCB size mismatch"
check_hash "$bcb_hash" "$candidate" candidate-bcb
test "$(stat -c %s "$backup")" = 1048576 || fail "misc backup size mismatch"
check_hash "$misc_hash" "$backup" host-misc-backup
test "$(cat "$host_marker")" = "HOST_SAVED_MISC_SHA256=$misc_hash" ||
    fail "host verification marker invalid"
check_hash "$misc_hash" "$misc" live-misc
test "$(cat "$authorization")" = 'BOOT STOCK RECOVERY FOR READ ONLY DUALBOOT PREFLIGHT' ||
    fail "authorization token invalid"

if test "$mode" = --check; then
    echo STOCK_RECOVERY_PREFLIGHT_READY_NO_CHANGES
    exit 0
fi

original_tail=$(tail_hash "$backup")
bcb_changed=0
committed=0
rollback_on_exit() {
    result=$?
    trap - 0 HUP INT TERM
    if test "$result" -ne 0 && test "$bcb_changed" = 1 && test "$committed" = 0; then
        echo STOCK_RECOVERY_PREFLIGHT_FAILED_RESTORING_MISC >&2
        if dd if="$backup" of="$misc" bs=1048576 count=1 conv=fsync status=none &&
                printf '%s  %s\n' "$misc_hash" "$misc" | sha256sum -c - >/dev/null; then
            echo STOCK_RECOVERY_MISC_ROLLBACK_VERIFIED >&2
        else
            echo STOCK_RECOVERY_MISC_ROLLBACK_FAILED_USE_HOST_BACKUP >&2
            exit 126
        fi
    fi
    exit "$result"
}
trap rollback_on_exit 0
trap 'exit 125' HUP INT TERM

# Mark the transaction as changed before dd so a partial write also rolls back.
bcb_changed=1
dd if="$candidate" of="$misc" bs=2048 count=1 conv=notrunc,fsync status=none
readback=$(dd if="$misc" bs=2048 count=1 status=none | sha256sum | awk '{print $1}')
test "$readback" = "$bcb_hash" || fail "BCB readback mismatch"
test "$(tail_hash "$misc")" = "$original_tail" || fail "misc bytes after BCB changed"
check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 recovery
check_hash fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f /dev/sda19 boot
committed=1
sync
echo STOCK_RECOVERY_PREFLIGHT_BCB_STAGED_NO_WIPE_RESTART_WITH_ORDERLY_HELPER
