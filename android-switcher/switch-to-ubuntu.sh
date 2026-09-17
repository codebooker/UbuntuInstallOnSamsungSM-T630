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
ubuntu_boot=eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb

fail() { echo "UBUNTU_SWITCH_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1
    path=$2
    label=$3
    echo "$expected  $path" | sha256sum -c - >/dev/null || fail "$label hash mismatch"
}
check_neighbors() {
    check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/block/by-name/recovery recovery
    check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/block/by-name/vendor_boot vendor_boot
    check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/block/by-name/dtbo dtbo
    check_hash a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/block/by-name/vbmeta vbmeta
}

test "$(id -u)" = 0 || fail "Magisk root authorization is required"
test "$(getprop ro.product.model)" = SM-T630 || fail "model mismatch"
test "$(getprop ro.build.version.incremental)" = T630XXSBDZE3 || fail "Android build mismatch"
test "$(getprop sys.boot_completed)" = 1 || fail "Android has not completed boot"
test "$(getprop ro.crypto.state)" = encrypted || fail "Android data is not encrypted"
grep -q ' /data f2fs ' /proc/mounts || fail "Android data is not mounted as F2FS"
grep -qx PARTNAME=linuxroot /sys/class/block/sda34/uevent || fail "linuxroot identity mismatch"
test "$(cat /sys/class/block/sda34/start)" = 21880832 || fail "linuxroot start mismatch"
test "$(cat /sys/class/block/sda34/size)" = 134217728 || fail "linuxroot size mismatch"
grep -qx PARTNAME=userdata /sys/class/block/sda35/uevent || fail "userdata identity mismatch"
test "$(cat /sys/class/block/sda35/start)" = 156098560 || fail "userdata start mismatch"
test "$(cat /sys/class/block/sda35/size)" = 92700632 || fail "userdata size mismatch"
test -d /sys/class/block/sda35/holders || fail "userdata holder state unavailable"
test -n "$(ls /sys/class/block/sda35/holders)" || fail "encrypted userdata mapping absent"
test "$(dd if=/dev/block/by-name/metadata bs=1 skip=1080 count=2 2>/dev/null |
    od -An -tx1 | tr -d ' \n')" = 53ef || fail "metadata is not ext4"
test -z "$(dd if=/dev/block/by-name/misc bs=32 count=1 2>/dev/null | tr -d '\000')" ||
    fail "misc contains a boot command"

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
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 50 || fail "battery below 50 percent"
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
dd if="$boot" of="$rollback" bs=4194304 2>/dev/null
check_hash "$android_boot" "$rollback" transaction-android-backup
changed=1
dd if="$ubuntu_image" of="$boot" bs=4194304 conv=fsync 2>/dev/null
sync
check_hash "$ubuntu_boot" "$boot" Ubuntu-BOOT-readback
check_neighbors
committed=1
sync
echo UBUNTU_BOOT_STAGED_READBACK_VERIFIED_RESTARTING
setprop sys.powerctl reboot
