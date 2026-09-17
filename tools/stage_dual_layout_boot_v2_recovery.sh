#!/bin/busybox sh
# Install the module-compatible dual-layout Ubuntu BOOT from recovery RAM.
set -eu

mode=${1:---check}
image=/run/t630-dual-layout-ubuntu-v2.img
rollback=/run/t630-dual-layout-v1.rollback.img
old_boot=eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb
new_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f

case "$mode" in
    --check|--write) ;;
    *) echo "usage: $0 [--check|--write]" >&2; exit 2 ;;
esac

test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
grep -qx PARTNAME=boot /sys/class/block/sda19/uevent
grep -qx PARTN=19 /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
test -z "$(ls /sys/class/block/sda19/holders)"
boot_dev=$(cat /sys/class/block/sda19/dev)
awk -v dev="$boot_dev" '$3 == dev { found=1 } END { exit found ? 1 : 0 }' \
    /proc/self/mountinfo
test -f "$image" && test ! -L "$image"
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_boot" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -
test ! -e "$rollback"

test "$(cat /sys/class/power_supply/battery/capacity)" -ge 50
status=$(cat /sys/class/power_supply/battery/status)
case "$status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
        test "$(cat /sys/class/power_supply/usb/online)" = 1
        ;;
    *) echo "tablet must be externally powered" >&2; exit 1 ;;
esac

check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors

if [ "$mode" = --check ]; then
    echo DUAL_LAYOUT_BOOT_V2_READY_NO_CHANGES
    exit 0
fi

backup_ready=0
committed=0
rollback_on_error() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$committed" != 1 ] && [ "$backup_ready" = 1 ]; then
        dd if="$rollback" of=/dev/sda19 bs=4M conv=fsync status=none || true
        sync
        echo "BOOT replacement failed; rollback attempted." >&2
    fi
    exit "$result"
}
trap rollback_on_error EXIT HUP INT TERM

dd if=/dev/sda19 of="$rollback" bs=4M status=none
printf '%s  %s\n' "$old_boot" "$rollback" | sha256sum -c -
backup_ready=1
dd if="$image" of=/dev/sda19 bs=4M conv=fsync status=none
sync
printf '%s  %s\n' "$new_boot" /dev/sda19 | sha256sum -c -
check_neighbors
committed=1
trap - EXIT HUP INT TERM
echo DUAL_LAYOUT_BOOT_V2_WRITTEN_READBACK_VERIFIED
