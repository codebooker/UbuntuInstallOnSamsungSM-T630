#!/bin/sh
# Install the module-compatible whole-disk/linuxroot Ubuntu BOOT only.
set -eu

mode=${1:---check}
artifact=/opt/t630/artifacts/dual-layout-ubuntu-v2
image=$artifact/boot.img
manifest=$artifact/manifest.json
rollback=$artifact/dual-layout-ubuntu-v1.transaction-rollback.img
old_boot=eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb
new_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f
manifest_hash=ac3c7e3477424c59e1babf852c7f3a37a5d5e8986122fe07fd05e1b2c7a291ec

case "$mode" in --check|--write) ;; *) echo "usage: $0 [--check|--write]" >&2; exit 2;; esac
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
grep -Fq 'OFFLINE_VALIDATED_DUAL_LAYOUT_NOT_FLASH_APPROVED' "$manifest"
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -

test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
status=$(cat /sys/class/power_supply/battery/status)
case "$status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
        test "$(cat /sys/class/power_supply/usb/online)" = 1
        ;;
    *) echo "external power is required: $status" >&2; exit 1;;
esac

check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors
if [ "$mode" = --check ]; then
    echo DUAL_LAYOUT_UBUNTU_V2_READY_NO_CHANGES
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
        echo 'Dual-layout staging failed; Ubuntu v1 rollback attempted.' >&2
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
echo DUAL_LAYOUT_UBUNTU_V2_STAGED_BOOT_ONLY_READBACK_VERIFIED
