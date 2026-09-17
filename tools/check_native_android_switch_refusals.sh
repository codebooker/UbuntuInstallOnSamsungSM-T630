#!/bin/sh
# Exercise Ubuntu-to-Android refusal gates without altering persistent files.
set -eu
export LC_ALL=C

root=/run/ubuntu
helper=/usr/local/sbin/t630-switch-to-native-android
artifact=$root/opt/t630/artifacts/native-android-stock

fail() { echo "SWITCH_REFUSAL_TEST_FAILED: $*" >&2; exit 1; }
check_hash() (
    expected=$1
    path=$2
    label=$3
    printf '%s  %s\n' "$expected" "$path" | sha256sum -c - >/dev/null ||
        fail "$label changed"
)
check_protected_storage() {
    check_hash fdc824381f5280e8135b61de33205f7b73c98c4edde8421d8f1eb6fdf051f45f /dev/sda19 boot
    check_hash 2b6901f8341de3b76fbcabc69bf0229683d503f233eafd580b4d602392ff74f5 /dev/sda20 recovery
    check_hash fbebd763c17c05bc162776a6e9abd86fc386aa0ef58ccfdaa6cb9b13a6a0c72f /dev/sda21 vendor_boot
    check_hash f9111b7a566b0a7342ec4d8f14cee53dc465a272d42596f774c0519d6e89fc57 /dev/sda22 dtbo
    check_hash a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225 /dev/sde19 vbmeta
}
expect_refusal() {
    refusal_label=$1
    wanted=$2
    shift 2
    set +e
    output=$("$@" 2>&1)
    result=$?
    set -e
    test "$result" = 1 || fail "$refusal_label returned $result instead of refusal status 1"
    printf '%s\n' "$output" | grep -F "NATIVE_ANDROID_SWITCH_REFUSED: $wanted" >/dev/null ||
        fail "$refusal_label did not report the expected refusal"
    check_protected_storage
    echo "SWITCH_REFUSAL_VERIFIED: $refusal_label"
}

test "$(id -u)" = 0 || fail "root is required"
test -x "$root$helper" || fail "installed switch helper is absent"
test -d "$artifact" && test ! -L "$artifact" || fail "artifact directory is unsafe"
command -v unshare >/dev/null || fail "unshare is unavailable"
command -v mount >/dev/null || fail "mount is unavailable"

work=$(mktemp -d /run/t630-switch-refusal.XXXXXX)
case "$work" in
    /run/t630-switch-refusal.*) ;;
    *) fail "temporary-directory boundary mismatch" ;;
esac
cleanup() {
    result=$?
    trap - 0 HUP INT TERM
    rm -f "$work/bad-hash" "$work/no-power" "$work/bad-neighbor"
    rmdir "$work" 2>/dev/null || true
    exit "$result"
}
trap cleanup 0 HUP INT TERM

printf '%064d\n' 0 >"$work/bad-hash"
printf 'Discharging\n' >"$work/no-power"
printf 'deliberately wrong protected-neighbor bytes\n' >"$work/bad-neighbor"
chmod 0600 "$work/bad-hash" "$work/no-power" "$work/bad-neighbor"

check_protected_storage
chroot "$root" "$helper" --check >/dev/null || fail "clean baseline check failed"

bad_image_hash() {
    unshare -m sh -c '
        set -eu
        mount --make-rprivate /
        mount --bind "$1/bad-hash" \
            /run/ubuntu/opt/t630/artifacts/native-android-stock/boot.sha256
        exec chroot /run/ubuntu /usr/local/sbin/t630-switch-to-native-android --check
    ' sh "$work"
}
no_external_power() {
    unshare -m sh -c '
        set -eu
        mount --make-rprivate /
        mount --bind "$1/no-power" \
            /run/ubuntu/sys/class/power_supply/battery/status
        exec chroot /run/ubuntu /usr/local/sbin/t630-switch-to-native-android --check
    ' sh "$work"
}
bad_recovery_neighbor() {
    unshare -m sh -c '
        set -eu
        mount --make-rprivate /
        mount --bind "$1/bad-neighbor" /run/ubuntu/dev/sda20
        exec chroot /run/ubuntu /usr/local/sbin/t630-switch-to-native-android --check
    ' sh "$work"
}

expect_refusal corrupt-image-hash 'accepted-android-boot hash mismatch' bad_image_hash
expect_refusal no-external-power 'external power is required' no_external_power
expect_refusal protected-neighbor-mismatch 'recovery hash mismatch' bad_recovery_neighbor

chroot "$root" "$helper" --check >/dev/null || fail "clean final check failed"
check_protected_storage
echo SWITCH_REFUSAL_GATES_PASSED_NO_PERSISTENT_CHANGES
