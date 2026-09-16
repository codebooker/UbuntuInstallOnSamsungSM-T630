#!/bin/sh
# Atomically install the isolated-namespace pivot_root fix while retaining v12.
set -eu

mode=${1:---check}
release=5.4.274-qgki-31225846-abT630XXSBDZE3
artifact=/opt/t630/artifacts/waydroid-kernel-v13
image=$artifact/boot.img
current_modules=/opt/t630/vendor/lib/modules
transaction_rollback=$artifact/boot-v12.transaction-rollback.img
stable_rollback=$artifact/boot-v12.stable-rollback.img
old_boot=ffd152fde55e5bf42c4ebd5b0ff028ac825553b66af9a3cb81dd97730ae77754
new_boot=1403afb30d584418ea6bfc011317f33bf8073294eae355d0c05d8d61c7355e76
module_manifest=d574e39844665e55a85549ea829ec20715ff29223786a4c4b8386b2486f24889

case "$mode" in
    --check|--write) ;;
    *) echo "usage: $0 [--check|--write]" >&2; exit 2 ;;
esac

test "$(id -u)" = 0
test "$(uname -r)" = "$release"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
grep -qx 'PARTNAME=boot' /sys/class/block/sda19/uevent
test "$(cat /sys/class/block/sda19/size)" = 196608
test -b /dev/sda19
boot_dev=$(cat /sys/class/block/sda19/dev)
awk -v dev="$boot_dev" '$3 == dev { found=1 } END { exit found ? 1 : 0 }' \
    /proc/self/mountinfo

for path in "$artifact" "$current_modules"; do
    test -d "$path"
    test ! -L "$path"
done
test ! -e "$transaction_rollback"
test "$(find "$current_modules" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 99
test -z "$(find "$current_modules" -type l -print -quit)"
test "$(sha256sum "$current_modules/manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
test "$(sha256sum "$artifact/module-payload-manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
cmp "$current_modules/manifest.json" "$artifact/module-payload-manifest.json"
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_boot" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -
printf '%s  %s\n' "$old_boot" "$stable_rollback" | sha256sum -c -

test "$(cat /sys/class/power_supply/battery/capacity)" -ge 30
battery_status=$(cat /sys/class/power_supply/battery/status)
case "$battery_status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
            test "$(cat /sys/class/power_supply/usb/online)" = 1
        ;;
    *) echo "battery is not charging: $battery_status" >&2; exit 1 ;;
esac

check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors

if [ "$mode" = --check ]; then
    echo WAYDROID_KERNEL_V13_TRIAL_READY_NO_CHANGES
    exit 0
fi

boot_backup_ready=0
committed=0
rollback() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$committed" != 1 ] && [ "$boot_backup_ready" = 1 ]; then
        dd if="$transaction_rollback" of=/dev/sda19 bs=4M conv=fsync status=none || true
        sync
        echo 'Waydroid v13 staging failed; v12 boot rollback attempted.' >&2
    fi
    exit "$result"
}
trap rollback EXIT HUP INT TERM

dd if=/dev/sda19 of="$transaction_rollback" bs=4M status=none
printf '%s  %s\n' "$old_boot" "$transaction_rollback" | sha256sum -c -
boot_backup_ready=1
dd if="$image" of=/dev/sda19 bs=4M conv=fsync status=none
sync
printf '%s  %s\n' "$new_boot" /dev/sda19 | sha256sum -c -
check_neighbors
printf '%s\n' "$new_boot" >"$artifact/trial-armed"
sync
committed=1
trap - EXIT HUP INT TERM
echo WAYDROID_KERNEL_V13_TRIAL_STAGED_BOOT_ONLY_READBACK_VERIFIED
