#!/bin/sh
# Atomically replace the contaminated v10 trial with the audited SM-T630 v12 pair.
set -eu

mode=${1:---check}
release=5.4.274-qgki-31225846-abT630XXSBDZE3
artifact=/opt/t630/artifacts/waydroid-kernel-v12
image=$artifact/boot.img
candidate=/opt/t630/vendor/lib/modules-waydroid-v12
current=/opt/t630/vendor/lib/modules
bad_profile=/opt/t630/vendor/lib/modules-waydroid-v10-bad-profile
stock_backup=/opt/t630/vendor/lib/modules-stock-v12
transaction_rollback=$artifact/boot-v10-bad-profile.rollback.img
stable_rollback=$artifact/boot-v12-stable.rollback.img
old_boot=b49f47288061ef294a35f3fcb9d2da51dd2721f85ea72b805838e6a9e9a25888
new_boot=ffd152fde55e5bf42c4ebd5b0ff028ac825553b66af9a3cb81dd97730ae77754
stock_boot=a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28
old_module_manifest=dc699395c132aae4ee536c82a33be7bf3d24a8eace00433b8e0a0cf91e527117
module_manifest=d574e39844665e55a85549ea829ec20715ff29223786a4c4b8386b2486f24889
module_symvers=37c1d3653adfe07978ed6b388d778a67c8b79690ff1eca34ce538624e4224277

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

for path in "$artifact" "$candidate" "$current" "$stock_backup"; do
    test -d "$path"
    test ! -L "$path"
done
test ! -e "$bad_profile"
test ! -e "$transaction_rollback"
test "$(find "$current" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 100
test "$(find "$candidate" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 99
test "$(find "$stock_backup" -maxdepth 1 -type f -name '*.ko' | wc -l)" = 103
test -z "$(find "$candidate" -type l -print -quit)"
test "$(sha256sum "$current/manifest.json" | cut -d' ' -f1)" = \
    "$old_module_manifest"
test "$(sha256sum "$candidate/manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
test "$(sha256sum "$artifact/module-payload-manifest.json" | cut -d' ' -f1)" = \
    "$module_manifest"
cmp "$candidate/manifest.json" "$artifact/module-payload-manifest.json"
test "$(stat -c %s "$image")" = 100663296
printf '%s  %s\n' "$new_boot" "$image" | sha256sum -c -
printf '%s  %s\n' "$old_boot" /dev/sda19 | sha256sum -c -
printf '%s  %s\n' "$stock_boot" "$stable_rollback" | sha256sum -c -

python3 - "$candidate" "$module_symvers" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
expected_symvers = sys.argv[2]
data = json.loads((root / 'manifest.json').read_text())
assert data['device'] == 'SM-T630'
assert data['firmware'] == 'T630XXSBDZE3'
assert data['project_name'] == 'gtact4prowifi'
assert data['audio_profile_header'] == 'lahaina_gtact4pro.h'
assert data['kernel_release'] == '5.4.274-qgki-31225846-abT630XXSBDZE3'
assert data['module_symvers_sha256'] == expected_symvers
assert data['coherent_module_count'] == 99
assert data['omitted_unused_modules'] == ['tas256x_dlkm.ko']
machine = next(item for item in data['modules']
               if item['file'] == 'machine_dlkm.ko')
assert 'tas256x_dlkm' not in machine['depends'].split(',')
assert 'snd-soc-cirrus-amp' in machine['depends'].split(',')
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

check_neighbors() {
    printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c -
    printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c -
    printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c -
    printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c -
}
check_neighbors

if [ "$mode" = --check ]; then
    echo WAYDROID_KERNEL_V12_TRIAL_READY_NO_CHANGES
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
            dd if="$transaction_rollback" of=/dev/sda19 bs=4M conv=fsync status=none || true
        fi
        if [ "$candidate_activated" = 1 ]; then
            if [ ! -e "$candidate" ] && [ -d "$current" ]; then
                mv "$current" "$candidate" || true
            fi
        fi
        if [ "$current_backed_up" = 1 ]; then
            if [ ! -e "$current" ] && [ -d "$bad_profile" ]; then
                mv "$bad_profile" "$current" || true
            fi
        fi
        sync
        echo 'Waydroid v12 staging failed; transaction rollback attempted.' >&2
    fi
    exit "$result"
}
trap rollback EXIT HUP INT TERM

dd if=/dev/sda19 of="$transaction_rollback" bs=4M status=none
printf '%s  %s\n' "$old_boot" "$transaction_rollback" | sha256sum -c -
boot_backup_ready=1
mv "$current" "$bad_profile"
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
echo WAYDROID_KERNEL_V12_TRIAL_STAGED_BOOT_AND_MODULES_READBACK_VERIFIED
