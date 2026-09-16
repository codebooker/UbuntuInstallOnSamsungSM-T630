#!/bin/sh
# Atomically pair the audited Waydroid kernel with its coherent module payload.
set -eu

mode=${1:---check}
release=5.4.274-qgki-31225846-abT630XXSBDZE3
artifact=/opt/t630/artifacts/waydroid-kernel-v10
image=$artifact/boot.img
candidate=/opt/t630/vendor/lib/modules-waydroid-v10
current=/opt/t630/vendor/lib/modules
backup=/opt/t630/vendor/lib/modules-stock-v12
rollback_image=$artifact/boot-v12.rollback.img
old_boot=a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28
new_boot=b49f47288061ef294a35f3fcb9d2da51dd2721f85ea72b805838e6a9e9a25888
module_manifest=1aa8d0fa62387f08d43378fdb92d268b8e9394f2558ebd0a2a046a1df3005370

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

for path in "$artifact" "$candidate" "$current"; do
    test -d "$path"
    test ! -L "$path"
done
test ! -e "$backup"
test ! -e "$rollback_image"
test "$(find "$current" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 103
test "$(find "$candidate" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 99
test -z "$(find "$candidate" -type l -print -quit)"
test "$(sha256sum "$current/qca_cld3_wlan.ko" | cut -d' ' -f1)" = \
    d4dc61be338e62612d5b492630894f1f1f9382c1650a7b7273f80277d88a611a
test "$(sha256sum "$candidate/manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
test "$(sha256sum "$artifact/module-payload-manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
cmp "$candidate/manifest.json" "$artifact/module-payload-manifest.json"
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_boot" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -

python3 - "$candidate" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
data = json.loads((root / 'manifest.json').read_text())
assert data['device'] == 'SM-T630'
assert data['firmware'] == 'T630XXSBDZE3'
assert data['kernel_release'] == '5.4.274-qgki-31225846-abT630XXSBDZE3'
assert data['coherent_module_count'] == 99
assert data['omitted_unused_modules'] == [
    'rmnet_core.ko', 'rmnet_ctl.ko', 'rmnet_offload.ko', 'rmnet_shs.ko'
]
records = data['modules'] + [dict(file=name, **value)
                             for name, value in data['metadata'].items()]
for item in records:
    path = root / item['file']
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == item['size']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
PY

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

# Verify protected neighbors before any write as well as after it.
check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors

if [ "$mode" = --check ]; then
    echo WAYDROID_KERNEL_V10_TRIAL_READY_NO_CHANGES
    exit 0
fi

current_backed_up=0
candidate_activated=0
boot_backup_ready=0
committed=0
rollback() {
    result=$?
    trap - EXIT HUP INT TERM
    if [ "$committed" != 1 ]; then
        if [ "$boot_backup_ready" = 1 ]; then
            dd if="$rollback_image" of=/dev/sda19 bs=4M conv=fsync status=none || true
        fi
        if [ "$candidate_activated" = 1 ]; then
            if [ ! -e "$candidate" ] && [ -d "$current" ]; then
                mv "$current" "$candidate" || true
            fi
        fi
        if [ "$current_backed_up" = 1 ]; then
            if [ ! -e "$current" ] && [ -d "$backup" ]; then
                mv "$backup" "$current" || true
            fi
        fi
        sync
        echo 'Waydroid kernel trial staging failed; rollback attempted.' >&2
    fi
    exit "$result"
}
trap rollback EXIT HUP INT TERM

dd if=/dev/sda19 of="$rollback_image" bs=4M status=none
printf '%s  %s\n' "$old_boot" "$rollback_image" | sha256sum -c -
boot_backup_ready=1
mv "$current" "$backup"
current_backed_up=1
mv "$candidate" "$current"
candidate_activated=1
sync
dd if="$image" of=/dev/sda19 bs=4M conv=fsync status=none
sync
printf '%s  %s\n' "$new_boot" /dev/sda19 | sha256sum -c -
check_neighbors
printf '%s\n' "$new_boot" >"$artifact/trial-armed"
sync
committed=1
trap - EXIT HUP INT TERM
echo WAYDROID_KERNEL_V10_TRIAL_STAGED_BOOT_AND_MODULES_READBACK_VERIFIED
