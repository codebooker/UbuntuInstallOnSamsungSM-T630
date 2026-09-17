#!/bin/sh
# Switch an already accepted encrypted native Android installation to stock BOOT.
set -eu
export LC_ALL=C

mode=${1:---check}
artifact=/opt/t630/artifacts/native-android-stock
image=$artifact/boot.img
ubuntu_rollback=$artifact/ubuntu-dual-layout.transaction-rollback.img
acceptance=/etc/t630/native-android-accepted
authorization=$artifact/AUTHORIZE-NATIVE-ANDROID-SWITCH
ubuntu_boot=eefb77383dc668926c6a2e95b7d1f862d96ab438ddcd5721c03e101df68fcbfb
android_boot=79a9b1d56763cb6e3c113473eb783f6332fe79b054e3c67494c5094c6c382796

case "$mode" in --check|--write) ;; *) echo "usage: $0 --check|--write" >&2; exit 2 ;; esac
fail() { echo "NATIVE_ANDROID_SWITCH_REFUSED: $*" >&2; exit 1; }
check_hash() {
    expected=$1
    path=$2
    label=$3
    printf '%s  %s\n' "$expected" "$path" | sha256sum -c - >/dev/null ||
        fail "$label hash mismatch"
}
is_mounted() {
    major_minor=$(cat "/sys/class/block/$1/dev")
    awk -v wanted="$major_minor" '$3 == wanted { found=1 } END { exit found ? 0 : 1 }' \
        /proc/self/mountinfo
}
check_neighbors() {
    check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 recovery
    check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 vendor_boot
    check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 dtbo
    check_hash a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 vbmeta
}

test "$(id -u)" = 0 || fail "root is required"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline || fail "model mismatch"
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3 || fail "kernel mismatch"
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1 ||
    fail "Ubuntu installation mismatch"
test "$(findmnt -n -o SOURCE /)" = /dev/sda34 || fail "Ubuntu root mismatch"
grep -qx PARTNAME=linuxroot /sys/class/block/sda34/uevent || fail "linuxroot identity mismatch"
test "$(cat /sys/class/block/sda34/start)" = 21880832 || fail "linuxroot start mismatch"
test "$(cat /sys/class/block/sda34/size)" = 134217728 || fail "linuxroot size mismatch"
grep -qx PARTNAME=userdata /sys/class/block/sda35/uevent || fail "userdata identity mismatch"
test "$(cat /sys/class/block/sda35/start)" = 156098560 || fail "userdata start mismatch"
test "$(cat /sys/class/block/sda35/size)" = 92700632 || fail "userdata size mismatch"
test -z "$(ls /sys/class/block/sda35/holders)" || fail "userdata has holders"
if is_mounted sda35; then fail "userdata is mounted"; fi

# After first Android boot, metadata encryption places the F2FS filesystem on a
# dm-default-key mapping. Raw p35 is ciphertext and must never be passed to an
# F2FS checker. The accepted marker records the earlier Android-side proof.
test -f "$acceptance" && test ! -L "$acceptance" || fail "Android acceptance marker absent"
test "$(stat -c %u "$acceptance")" = 0 || fail "Android acceptance marker is not root-owned"
test "$(cat "$acceptance")" = \
    'SM-T630 DZE3 NATIVE ANDROID FBE ACCEPTED; RAW USERDATA IS CIPHERTEXT' ||
    fail "Android acceptance marker invalid"
raw_magic=$(dd if=/dev/sda35 bs=1 skip=1024 count=4 status=none |
    od -An -tx1 | tr -d ' \n')
test "$raw_magic" != 1020f5f2 || fail "userdata unexpectedly exposes plaintext F2FS"
filesystem_type=$(blkid -p -s TYPE -o value /dev/sda35 2>/dev/null || true)
test -z "$filesystem_type" || fail "encrypted userdata exposes a raw filesystem"
test "$(dd if=/dev/sda25 bs=1 skip=1080 count=2 status=none |
    od -An -tx1 | tr -d ' \n')" = 53ef || fail "metadata is not ext4"
test -z "$(dd if=/dev/sda10 bs=32 count=1 status=none | tr -d '\000')" ||
    fail "misc contains a boot command"

test -d "$artifact" && test ! -L "$artifact" || fail "Android artifact directory absent"
for path in "$image" "$ubuntu_rollback"; do
    test -f "$path" && test ! -L "$path" || fail "$path is absent or unsafe"
    test "$(stat -c %u "$path")" = 0 || fail "$path is not root-owned"
    test "$(stat -c %s "$path")" = 100663296 || fail "$path size mismatch"
done
check_hash "$android_boot" "$image" stock-android-boot
check_hash "$ubuntu_boot" "$ubuntu_rollback" accepted-ubuntu-rollback
check_hash "$ubuntu_boot" /dev/sda19 installed-ubuntu-boot
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
sgdisk --verify /dev/sda >/tmp/t630-gpt-before-android-switch.txt 2>&1 ||
    fail "GPT verification failed"
grep -q 'No problems found' /tmp/t630-gpt-before-android-switch.txt || fail "GPT problems reported"
check_neighbors

if test "$mode" = --check; then
    echo NATIVE_ANDROID_ENCRYPTED_INSTALLATION_READY_NO_CHANGES
    exit 0
fi
test -f "$authorization" && test ! -L "$authorization" || fail "authorization absent"
test "$(stat -c %u "$authorization")" = 0 || fail "authorization is not root-owned"
test "$(cat "$authorization")" = 'SWITCH SM-T630 FROM ACCEPTED UBUNTU TO ACCEPTED NATIVE ANDROID' ||
    fail "authorization invalid"

boot_changed=0
committed=0
rollback_on_exit() {
    result=$?
    trap - 0 HUP INT TERM
    if test "$result" -ne 0 && test "$boot_changed" = 1 && test "$committed" = 0; then
        echo NATIVE_ANDROID_SWITCH_FAILED_RESTORING_UBUNTU >&2
        if dd if="$ubuntu_rollback" of=/dev/sda19 bs=4194304 conv=fsync status=none &&
                printf '%s  %s\n' "$ubuntu_boot" /dev/sda19 | sha256sum -c - >/dev/null; then
            echo NATIVE_ANDROID_SWITCH_ROLLBACK_VERIFIED >&2
        else
            echo NATIVE_ANDROID_SWITCH_ROLLBACK_FAILED_USE_DOWNLOAD_MODE >&2
            exit 126
        fi
    fi
    exit "$result"
}
trap rollback_on_exit 0
trap 'exit 125' HUP INT TERM
boot_changed=1
dd if="$image" of=/dev/sda19 bs=4194304 conv=fsync status=none
sync
check_hash "$android_boot" /dev/sda19 Android-BOOT-readback
check_neighbors
committed=1
sync
echo NATIVE_ANDROID_ACCEPTED_BOOT_STAGED_READBACK_VERIFIED_RESTART_MANUALLY
