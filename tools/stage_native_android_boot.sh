#!/bin/sh
# Switch only BOOT from accepted dual-layout Ubuntu to exact DZE3 Android.
set -eu
export LC_ALL=C

mode=${1:---check}
artifact=/opt/t630/artifacts/native-android-stock
image=$artifact/boot.img
rollback=$artifact/ubuntu-dual-layout.transaction-rollback.img
authorization=$artifact/AUTHORIZE-NATIVE-ANDROID-BOOT
ubuntu_boot=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f
android_boot=79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796

case "$mode" in --check|--write) ;; *) echo "usage: $0 --check|--write" >&2; exit 2 ;; esac
fail() { echo "NATIVE_ANDROID_BOOT_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1
    path=$2
    label=$3
    printf '%s  %s\n' "$expected" "$path" | sha256sum -c - >/dev/null ||
        fail "$label hash mismatch"
}
check_vbmeta() {
    actual=$(sha256sum "$1" | awk '{print $1}')
    case "$actual" in
        a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225|9d3e15453eb2fd1058365dd8fc99199fd2ad6f44a53de22b92f01f06d90a747e) ;;
        *) fail "vbmeta hash mismatch" ;;
    esac
}
check_neighbors() {
    check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 recovery
    check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 vendor_boot
    check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 dtbo
    check_vbmeta /dev/sde19
}

test "$(id -u)" = 0 || fail "root is required"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline || fail "model mismatch"
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3 || fail "kernel mismatch"
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1 ||
    fail "Ubuntu installation mismatch"
grep -qx PARTNAME=boot /sys/class/block/sda19/uevent || fail "BOOT identity mismatch"
test "$(cat /sys/class/block/sda19/size)" = 196608 || fail "BOOT size mismatch"
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

# Stock recovery must initialize both Android data and its encryption metadata
# before stock Android BOOT is accepted for staging.
test "$(dd if=/dev/sda35 bs=1 skip=1024 count=4 status=none |
    od -An -tx1 | tr -d ' \n')" = 1020f5f2 || fail "userdata is not F2FS"
test "$(dd if=/dev/sda25 bs=1 skip=1080 count=2 status=none |
    od -An -tx1 | tr -d ' \n')" = 53ef || fail "metadata is not ext4"
test -x /usr/sbin/fsck.f2fs || fail "fsck.f2fs is unavailable"
/usr/sbin/fsck.f2fs --dry-run /dev/sda35 >/tmp/t630-native-userdata-fsck.txt 2>&1 ||
    fail "userdata F2FS check failed"

# Recovery must have consumed and cleared boot-recovery before switching BOOT.
test -z "$(dd if=/dev/sda10 bs=32 count=1 status=none | tr -d '\000')" ||
    fail "misc still contains a boot command"
test -d "$artifact" && test ! -L "$artifact" || fail "Android artifact directory absent"
test -f "$image" && test ! -L "$image" || fail "stock Android BOOT absent"
test "$(stat -c %s "$image")" = 100663296 || fail "stock Android BOOT size mismatch"
check_hash "$android_boot" "$image" stock-android-boot
check_hash "$ubuntu_boot" /dev/sda19 installed-ubuntu-boot
test ! -e "$rollback" || fail "rollback path already exists"
test "$(cat /sys/class/power_supply/battery/capacity)" -ge 50 || fail "battery below 50 percent"
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
sgdisk --verify /dev/sda >/tmp/t630-gpt-before-android-boot.txt 2>&1 || fail "GPT verification failed"
grep -q 'No problems found' /tmp/t630-gpt-before-android-boot.txt || fail "GPT problems reported"
check_neighbors

if test "$mode" = --check; then
    echo NATIVE_ANDROID_STOCK_BOOT_READY_NO_CHANGES
    exit 0
fi
test -f "$authorization" && test ! -L "$authorization" || fail "authorization absent"
test "$(stat -c %u "$authorization")" = 0 || fail "authorization is not root-owned"
test "$(cat "$authorization")" = 'WRITE EXACT DZE3 STOCK ANDROID BOOT TO SM-T630' ||
    fail "authorization invalid"

backup_ready=0
committed=0
rollback_on_exit() {
    result=$?
    trap - 0 HUP INT TERM
    if test "$result" -ne 0 && test "$backup_ready" = 1 && test "$committed" = 0; then
        echo NATIVE_ANDROID_BOOT_FAILED_RESTORING_UBUNTU >&2
        if dd if="$rollback" of=/dev/sda19 bs=4194304 conv=fsync status=none &&
                printf '%s  %s\n' "$ubuntu_boot" /dev/sda19 | sha256sum -c - >/dev/null; then
            echo NATIVE_ANDROID_BOOT_ROLLBACK_VERIFIED >&2
        else
            echo NATIVE_ANDROID_BOOT_ROLLBACK_FAILED_USE_MAINTENANCE >&2
            exit 126
        fi
    fi
    exit "$result"
}
trap rollback_on_exit 0
trap 'exit 125' HUP INT TERM
dd if=/dev/sda19 of="$rollback" bs=4194304 status=none
check_hash "$ubuntu_boot" "$rollback" transaction-rollback
backup_ready=1
dd if="$image" of=/dev/sda19 bs=4194304 conv=fsync status=none
sync
check_hash "$android_boot" /dev/sda19 Android-BOOT-readback
check_neighbors
committed=1
sync
echo NATIVE_ANDROID_STOCK_BOOT_STAGED_READBACK_VERIFIED_RESTART_MANUALLY
