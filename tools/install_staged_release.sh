#!/bin/busybox sh
# Exact SM-T630 DZE3 installer. Default is read-only; --apply erases userdata.
set -eu

mode=${1:---check}
case "$mode" in
    --check|--apply) ;;
    *) echo "usage: $0 [--check|--apply]" >&2; exit 2 ;;
esac

stage=/run/t630-installer
runtime=/run/t630-installer-runtime
target=/run/t630-install-target
device=/dev/sda34
loader=$runtime/lib/ld-linux-aarch64.so.1
library_path=$runtime/lib/aarch64-linux-gnu:$runtime/usr/lib/aarch64-linux-gnu:$runtime/lib
authorization=$stage/ERASE-SM-T630-USERDATA
started=/run/t630-format-started
boot_hash=a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28

fail() { echo "INSTALLER_REFUSED: $*" >&2; exit 1; }

test "$(id -u)" = 0 || fail "root is required"
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3 ||
    fail "kernel baseline mismatch"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline || fail "model mismatch"
grep -qx 'PARTNAME=userdata' /sys/class/block/sda34/uevent || fail "userdata name mismatch"
grep -qx 'PARTN=34' /sys/class/block/sda34/uevent || fail "userdata number mismatch"
test "$(cat /sys/class/block/sda34/dev)" = 259:18 || fail "userdata device mismatch"
test "$(cat /sys/class/block/sda34/size)" = 226918360 || fail "userdata size mismatch"
test -b "$device" || fail "userdata block device absent"
test -z "$(ls /sys/class/block/sda34/holders)" || fail "userdata has block holders"
awk '$3 == "259:18" { found=1 } END { exit found ? 0 : 1 }' /proc/self/mountinfo &&
    fail "userdata is mounted"
test ! -e "$target" || fail "target path already exists"
test ! -e "$started" || fail "a format was already attempted this boot"

capacity=$(cat /sys/class/power_supply/battery/capacity)
test "$capacity" -ge 50 || fail "battery must be at least 50 percent"
status=$(cat /sys/class/power_supply/battery/status)
case "$status" in
    Charging) ;;
    Full)
        test "$(cat /sys/class/power_supply/ac/online)" = 1 ||
        test "$(cat /sys/class/power_supply/usb/online)" = 1 ||
            fail "full battery is not externally powered"
        ;;
    *) fail "tablet must be externally powered" ;;
esac

test -d "$stage" && test ! -L "$stage" || fail "RAM staging directory absent"
cd "$stage"
sha256sum -c SHA256SUMS >/dev/null || fail "staged checksums failed"
printf '%s  %s\n' "$boot_hash" boot/boot.img | sha256sum -c - >/dev/null ||
    fail "bundle BOOT is not accepted v12"
printf '%s  %s\n' "$boot_hash" /dev/sda19 | sha256sum -c - >/dev/null ||
    fail "installed BOOT is not accepted v12"
printf '%s  %s\n' 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 | sha256sum -c - >/dev/null || fail "recovery mismatch"
printf '%s  %s\n' fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 | sha256sum -c - >/dev/null || fail "vendor_boot mismatch"
printf '%s  %s\n' f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 | sha256sum -c - >/dev/null || fail "dtbo mismatch"
printf '%s  %s\n' a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 | sha256sum -c - >/dev/null || fail "vbmeta mismatch"

if [ ! -e "$runtime" ]; then
    mkdir -m 0700 "$runtime"
    if ! tar -xzf t630-installer-runtime.tar.gz -C "$runtime"; then
        rm -rf "$runtime"
        fail "installer runtime extraction failed"
    fi
else
    test -d "$runtime" && test ! -L "$runtime" ||
        fail "installer runtime path is unsafe"
fi
test -f "$loader" && test ! -L "$loader" || fail "runtime loader absent"
for tool in usr/sbin/mke2fs usr/sbin/e2fsck usr/bin/tar usr/bin/dpkg-query; do
    test -f "$runtime/$tool" && test ! -L "$runtime/$tool" ||
        fail "runtime tool absent: $tool"
done
run() { "$loader" --library-path "$library_path" "$@"; }
export MKE2FS_CONFIG=$runtime/etc/mke2fs.conf
run "$runtime/usr/bin/tar" --version | grep -q 'GNU tar' || fail "GNU tar runtime invalid"
run "$runtime/usr/sbin/mke2fs" -V >/dev/null 2>&1 || fail "mke2fs runtime invalid"
run "$runtime/usr/sbin/e2fsck" -V >/dev/null 2>&1 || fail "e2fsck runtime invalid"
run "$runtime/usr/bin/dpkg-query" --version >/dev/null 2>&1 || fail "dpkg-query runtime invalid"

if [ "$mode" = --check ]; then
    echo INSTALLER_CHECK_PASSED_USERDATA_UNMOUNTED_NO_DEVICE_WRITE
    exit 0
fi

test -f "$authorization" && test ! -L "$authorization" ||
    fail "authorization token absent"
test "$(cat "$authorization")" = 'ERASE SM-T630 USERDATA /dev/sda34 226918360' ||
    fail "authorization token invalid"
( set -C; : >"$started" ) 2>/dev/null || fail "cannot lock format attempt"

echo INSTALLER_APPLY_AUTHORIZED_FORMATTING_EXACT_USERDATA
run "$runtime/usr/sbin/mke2fs" -t ext4 -F -L ubuntu-t630 \
    -U 64de8544-53ea-4fdc-8946-d6b07e238630 -m 1 -i 65536 \
    -O '^orphan_file,^metadata_csum_seed' \
    -E nodiscard,lazy_itable_init=0,lazy_journal_init=0 "$device"
mkdir -m 0755 "$target"
mount -t ext4 -o noatime,errors=remount-ro "$device" "$target"
set -o pipefail
tar_failed=0
gzip -dc "$stage/t630-release-rootfs.tar.gz" |
    run "$runtime/usr/bin/tar" --numeric-owner --same-owner --acls --xattrs \
        '--xattrs-include=*' -xpf - -C "$target" || tar_failed=1
if [ "$tar_failed" -ne 0 ]; then
    sync
    umount "$target" || true
    fail "rootfs extraction failed after format"
fi

test "$(cat "$target/etc/t630-install-id")" = \
    SM-T630-T630XXSBDZE3-Ubuntu-v1 || fail "installed marker mismatch"
test "$(cat "$target/.t630-offline-root")" = \
    'SM-T630 OFFLINE RELEASE ROOT' || fail "offline root marker mismatch"
test ! -s "$target/etc/machine-id" || fail "machine identity is not blank"
test ! -e "$target/etc/t630/owner" || fail "owner state leaked into install"
test -z "$(find "$target/home" -mindepth 1 -maxdepth 1 -print -quit)" ||
    fail "home data leaked into install"
if awk -F: '$3 >= 1000 && $3 < 60000 { found=1 } END { exit found ? 0 : 1 }' \
        "$target/etc/passwd"; then
    fail "human account leaked into install"
fi
package_state=$(run "$runtime/usr/bin/dpkg-query" --root="$target" -W \
    '-f=${db:Status-Status} ${Version}\n' t630-release-base)
test "$package_state" = 'installed 0.1.18' || fail "release package state mismatch"
test ! -e "$target/etc/ssh/ssh_host_rsa_key" || fail "SSH host key leaked"
test ! -e "$target/etc/NetworkManager/system-connections" ||
    test -z "$(find "$target/etc/NetworkManager/system-connections" \
        -mindepth 1 -print -quit)" || fail "network credentials leaked"

sync
umount "$target"
run "$runtime/usr/sbin/e2fsck" -fn "$device"
rmdir "$target"
sync
echo INSTALLER_APPLY_COMPLETE_ROOT_VERIFIED_REBOOT_REQUIRED
