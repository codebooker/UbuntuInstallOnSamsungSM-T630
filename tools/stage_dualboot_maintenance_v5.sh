#!/bin/sh
# Write only the RAM preflight BOOT, retaining dual-layout Ubuntu rollback.
set -eu

mode=${1:---check}
artifact=/opt/t630/artifacts/dualboot-maintenance-v5
image=$artifact/boot.img
manifest=$artifact/manifest.json
rollback=$artifact/dual-layout-ubuntu-v2.transaction-rollback.img
old_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f
new_boot=c45e960fcbc6a30ab98872529d27a157a41409ea7601166330956b7f6e74ea4e
manifest_hash=635537b32539ed17afdfbd155c7da65ab6bc128315fdb628189c72938c228083

case "$mode" in
    --check|--write) ;;
    *) echo "usage: $0 [--check|--write]" >&2; exit 2 ;;
esac

test "$(id -u)" = 0
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
grep -qx 'PARTNAME=boot' /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
test -d "$artifact" && test ! -L "$artifact"
test -f "$image" && test ! -L "$image"
test -f "$manifest" && test ! -L "$manifest"
test ! -e "$rollback"
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_boot" "$image" | sha256sum -c -
printf '%s  %s\n' "$manifest_hash" "$manifest" | sha256sum -c -
grep -Fq 'OFFLINE_VALIDATED_PREFLIGHT_WITH_PINNED_BOOT_RESTORE_NOT_FLASH_APPROVED' "$manifest"
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -

test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
status=$(cat /sys/class/power_supply/battery/status)
case "$status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
        test "$(cat /sys/class/power_supply/usb/online)" = 1
        ;;
    *) echo "external power is required: $status" >&2; exit 1 ;;
esac

check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors

if [ "$mode" = --check ]; then
    echo DUALBOOT_MAINTENANCE_V5_READY_NO_CHANGES
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
        echo 'Maintenance staging failed; Ubuntu BOOT rollback attempted.' >&2
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
echo DUALBOOT_MAINTENANCE_V5_STAGED_BOOT_ONLY_READBACK_VERIFIED
