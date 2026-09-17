#!/system/bin/sh
# Atomically update only the installed Android-side Ubuntu switch payload.
set -eu
export PATH=/system/bin:/system/xbin:/vendor/bin

mode=${1:---check}
case "$mode" in --check|--apply) ;; *) echo "usage: $0 --check|--apply" >&2; exit 2 ;; esac

state=/data/adb/t630
incoming_image=/data/local/tmp/t630-ubuntu-boot-v2.img
incoming_helper=/data/local/tmp/t630-switch-to-ubuntu-v2
installed_image=$state/ubuntu-boot.img
installed_helper=$state/switch-to-ubuntu
android_hash_file=$state/android-boot.sha256
boot=/dev/block/by-name/boot
old_ubuntu=eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb
new_ubuntu=fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f
new_helper=cc7dd9b2ff0c84295031c36bb94dfa534570fa9e75097030c3170b116aa30c60

fail() { echo "ANDROID_SWITCH_UPDATE_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1 path=$2 label=$3
    echo "$expected  $path" | sha256sum -c - >/dev/null || fail "$label hash mismatch"
}

test "$(id -u)" = 0 || fail "Magisk root is required"
test "$(getprop ro.product.model)" = SM-T630 || fail "model mismatch"
test "$(getprop ro.build.version.incremental)" = T630XXSBDZE3 || fail "Android build mismatch"
test "$(getprop sys.boot_completed)" = 1 || fail "Android boot is incomplete"
test "$(getprop ro.crypto.state)" = encrypted || fail "Android data is not encrypted"
grep -q ' /data f2fs ' /proc/mounts || fail "Android data is not F2FS"
test -d "$state" && test ! -L "$state" || fail "switch state directory absent"
for path in "$installed_image" "$installed_helper" "$android_hash_file"; do
    test -f "$path" && test ! -L "$path" || fail "$path is absent or unsafe"
    test "$(stat -c %u "$path")" = 0 || fail "$path is not root-owned"
done
android_boot=$(cat "$android_hash_file")
case "$android_boot" in ''|*[!0-9a-f]*) fail "Android BOOT hash is malformed" ;; esac
test "${#android_boot}" = 64 || fail "Android BOOT hash length mismatch"
check_hash "$android_boot" "$boot" installed-android-boot

current_ubuntu=$(sha256sum "$installed_image" | awk '{print $1}')
case "$current_ubuntu" in
    "$old_ubuntu"|"$new_ubuntu") ;;
    *) fail "installed Ubuntu image is not an accepted generation" ;;
esac
test "$(stat -c %s "$incoming_image")" = 100663296 || fail "incoming Ubuntu image size mismatch"
check_hash "$new_ubuntu" "$incoming_image" incoming-ubuntu-boot
check_hash "$new_helper" "$incoming_helper" incoming-helper
grep -q "ubuntu_boot=$new_ubuntu" "$incoming_helper" || fail "helper does not pin BOOT v2"

if test "$mode" = --check; then
    echo ANDROID_SWITCH_PAYLOAD_V2_READY_NO_CHANGES
    exit 0
fi

new_image=$state/.ubuntu-boot-v2.new
new_script=$state/.switch-to-ubuntu-v2.new
test ! -e "$new_image" && test ! -e "$new_script" || fail "stale update files exist"
cleanup() { rm -f "$new_image" "$new_script"; }
trap cleanup 0 HUP INT TERM
cp "$incoming_image" "$new_image"
cp "$incoming_helper" "$new_script"
chown 0:0 "$new_image" "$new_script"
chmod 0400 "$new_image"
chmod 0700 "$new_script"
check_hash "$new_ubuntu" "$new_image" staged-ubuntu-boot
check_hash "$new_helper" "$new_script" staged-helper
mv -f "$new_image" "$installed_image"
sync
check_hash "$new_ubuntu" "$installed_image" installed-ubuntu-boot-v2
mv -f "$new_script" "$installed_helper"
sync
check_hash "$new_helper" "$installed_helper" installed-helper-v2
trap - 0 HUP INT TERM
echo ANDROID_SWITCH_PAYLOAD_V2_INSTALLED_NO_PARTITION_WRITE
