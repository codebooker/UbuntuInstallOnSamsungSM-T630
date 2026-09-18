#!/system/bin/sh
# Root-only Android half of the SM-T630 BOOT switch transaction.
set -eu
export PATH=/system/bin:/system/xbin:/vendor/bin

mode=${1:---check}
case "$mode" in
    --check|--switch-and-reboot) ;;
    *) echo "usage: $0 --check|--switch-and-reboot" >&2; exit 2 ;;
esac

state=/data/adb/t630
ubuntu_image=$state/ubuntu-boot.img
android_hash_file=$state/android-boot.sha256
rollback=$state/android-boot.transaction-rollback.img
boot=/dev/block/by-name/boot
journal=$state/last-ubuntu-switch
journal_new=$state/.last-ubuntu-switch.new
ubuntu_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f

fail() { echo "UBUNTU_SWITCH_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1
    path=$2
    label=$3
    echo "$expected  $path" | sha256sum -c - >/dev/null || fail "$label hash mismatch"
}
check_vbmeta() {
    actual=$(sha256sum "$1" | awk '{print $1}')
    case "$actual" in
        a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225|9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e) ;;
        *) fail "vbmeta hash mismatch" ;;
    esac
}
check_neighbors() {
    check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/block/by-name/recovery recovery
    check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/block/by-name/vendor_boot vendor_boot
    check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/block/by-name/dtbo dtbo
    check_vbmeta /dev/block/by-name/vbmeta
}

test "$(id -u)" = 0 || fail "Magisk root authorization is required"
test "$(getprop ro.product.model)" = SM-T630 || fail "model mismatch"
test "$(getprop ro.build.version.incremental)" = T630XXSBDZE3 || fail "Android build mismatch"
test "$(getprop sys.boot_completed)" = 1 || fail "Android has not completed boot"
test "$(getprop ro.crypto.state)" = encrypted || fail "Android data is not encrypted"
grep -q ' /data f2fs ' /proc/mounts || fail "Android data is not mounted as F2FS"
test "$(readlink -f "$boot")" = /dev/block/sda19 || fail "BOOT device mapping mismatch"
test "$(awk '$4 == "sda19" { print $3 }' /proc/partitions)" = 98304 ||
    fail "BOOT size mismatch"
test "$(readlink -f /dev/block/by-name/linuxroot)" = /dev/block/sda34 ||
    fail "linuxroot identity mismatch"
test "$(awk '$4 == "sda34" { print $3 }' /proc/partitions)" = 67108864 ||
    fail "linuxroot size mismatch"
test "$(readlink -f /dev/block/by-name/userdata)" = /dev/block/sda35 ||
    fail "userdata identity mismatch"
test "$(awk '$4 == "sda35" { print $3 }' /proc/partitions)" = 46350316 ||
    fail "userdata size mismatch"
awk '$2 == "/data" && $1 ~ /^\/dev\/block\/dm-[0-9]+$/ && $3 == "f2fs" { found=1 }
    END { exit found ? 0 : 1 }' /proc/mounts || fail "encrypted userdata mapping absent"
test "$(dd if=/dev/block/by-name/metadata bs=1 skip=1080 count=2 2>/dev/null |
    od -An -tx1 | tr -d ' \n')" = 53ef || fail "metadata is not ext4"
test "$(getprop ro.boot.boot_recovery)" = 0 || fail "Android booted through recovery"

test -d "$state" && test ! -L "$state" || fail "switch state directory absent"
for path in "$ubuntu_image" "$android_hash_file"; do
    test -f "$path" && test ! -L "$path" || fail "$path is absent or unsafe"
    test "$(stat -c %u "$path")" = 0 || fail "$path is not root-owned"
done
test "$(stat -c %s "$ubuntu_image")" = 100663296 || fail "Ubuntu BOOT size mismatch"
check_hash "$ubuntu_boot" "$ubuntu_image" accepted-ubuntu-boot
android_boot=$(cat "$android_hash_file")
case "$android_boot" in
    ''|*[!0-9a-f]*) fail "Android BOOT hash is malformed" ;;
    *) ;;
esac
test "${#android_boot}" = 64 || fail "Android BOOT hash length mismatch"
check_hash "$android_boot" "$boot" installed-android-boot
battery=$(dumpsys battery)
level=$(printf '%s\n' "$battery" | awk '$1 == "level:" { print $2; exit }')
test -n "$level" && test "$level" -ge 50 || fail "battery below 50 percent"
printf '%s\n' "$battery" | awk '
    $1 == "AC" && $2 == "powered:" && $3 == "true" { powered=1 }
    $1 == "USB" && $2 == "powered:" && $3 == "true" { powered=1 }
    $1 == "Wireless" && $2 == "powered:" && $3 == "true" { powered=1 }
    $1 == "Dock" && $2 == "powered:" && $3 == "true" { powered=1 }
    END { exit powered ? 0 : 1 }
' || fail "external power is required"
check_neighbors

if test "$mode" = --check; then
    echo UBUNTU_SWITCH_READY
    exit 0
fi

changed=0
committed=0
rollback_on_exit() {
    result=$?
    trap - 0 HUP INT TERM
    if test "$result" -ne 0 && test "$changed" = 1 && test "$committed" = 0; then
        echo UBUNTU_SWITCH_FAILED_RESTORING_ANDROID >&2
        if dd if="$rollback" of="$boot" bs=4194304 conv=fsync 2>/dev/null &&
                echo "$android_boot  $boot" | sha256sum -c - >/dev/null; then
            echo UBUNTU_SWITCH_ANDROID_ROLLBACK_VERIFIED >&2
        else
            echo UBUNTU_SWITCH_ROLLBACK_FAILED_USE_DOWNLOAD_MODE >&2
            exit 126
        fi
    fi
    exit "$result"
}
trap rollback_on_exit 0
trap 'exit 125' HUP INT TERM
test ! -e "$journal_new" || fail "stale switch journal transaction"
dd if="$boot" of="$rollback" bs=4194304 2>/dev/null
check_hash "$android_boot" "$rollback" transaction-android-backup
changed=1
dd if="$ubuntu_image" of="$boot" bs=4194304 conv=fsync 2>/dev/null
sync
blockdev --flushbufs "$boot"
check_hash "$ubuntu_boot" "$boot" Ubuntu-BOOT-readback
sleep 2
blockdev --flushbufs "$boot"
check_hash "$ubuntu_boot" "$boot" Ubuntu-BOOT-durable-readback
check_neighbors
(
    umask 077
    printf 'status=ubuntu-boot-durable-readback-verified\nboot_device=/dev/block/sda19\nboot_sha256=%s\n' \
        "$ubuntu_boot" >"$journal_new"
    chown 0:0 "$journal_new"
    chmod 0600 "$journal_new"
    mv -f "$journal_new" "$journal"
    sync
)
committed=1
sync
echo UBUNTU_BOOT_STAGED_READBACK_VERIFIED_RESTARTING
setprop sys.powerctl reboot
