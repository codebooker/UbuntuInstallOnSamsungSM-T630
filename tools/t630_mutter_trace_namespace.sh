#!/bin/sh
# Manual lab helper only: run after privileged unshare --mount, then chroot.
# Never bind over distro libraries in PID1's namespace or shared mount trees.
set -eu
case "$#:${1:-}" in
    0:) check_only=0 ;;
    1:--check-only) check_only=1 ;;
    *) echo 'No arbitrary launch commands are accepted.' >&2; exit 1 ;;
esac
test "$(id -u)" = 0
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test "${T630_MUTTER_PEN_TRACE:-0}" = 1
test "${T630_PEN_METADATA_TRIAL:-0}" = 1
test "${T630_GPU_RENDERER:-0}" = 0
test "$(readlink /proc/self/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"
if grep -q ' shared:' /proc/self/mountinfo; then
    echo 'Refusing a trace bind in a shared mount tree.' >&2
    exit 1
fi
stage=/run/t630-mutter-pen-trace-20260915
target=/usr/lib/aarch64-linux-gnu/mutter-14
test "$(stat -c '%u:%a' "$stage")" = 0:755
test -d "$target"
test -r "$stage/libmutter-cogl-14.so.0"
test -r "$stage/Cogl-14.typelib"
/usr/bin/mount --bind "$stage" "$target"
/usr/bin/mount -o remount,bind,ro "$target"
test "$(stat -Lc '%d:%i' "$target/libmutter-cogl-14.so.0")" = \
     "$(stat -Lc '%d:%i' "$stage/libmutter-cogl-14.so.0")"
test "$(stat -Lc '%d:%i' "$target/Cogl-14.typelib")" = \
     "$(stat -Lc '%d:%i' "$stage/typelibs/Cogl-14.typelib")"
echo 'PRIVATE_TRACE_MOUNT_CONFIRMED; normal desktop namespace unchanged.'
if [ "$check_only" = 1 ]; then
    exit 0
fi
# Keep the existing managed-session and normal-user authentication path.
exec /usr/local/bin/t630-gnome-preview
