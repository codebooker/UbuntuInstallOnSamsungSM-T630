#!/bin/busybox sh
# Stop Ubuntu and unmount linuxroot while preserving the RAM-staged installer.
set -eu

root=/run/ubuntu
stage=/run/t630-installer

fail() { echo "INSTALLER_PREPARE_REFUSED: $*" >&2; exit 1; }

test "$(id -u)" = 0 || fail "root is required"
test "$(uname -r)" = 5.4.274-qgki-31225846-abT630XXSBDZE3 ||
    fail "kernel baseline mismatch"
grep -q 'androidboot.em.model=SM-T630' /proc/cmdline || fail "model mismatch"
grep -qx 'PARTNAME=linuxroot' /sys/class/block/sda34/uevent ||
    fail "linuxroot identity mismatch"
test "$(cat /sys/class/block/sda34/size)" = 134217728 ||
    fail "linuxroot size mismatch"
grep -qx 'PARTNAME=userdata' /sys/class/block/sda35/uevent ||
    fail "Android userdata identity mismatch"
test "$(cat /sys/class/block/sda35/size)" = 92700632 ||
    fail "Android userdata size mismatch"
test -d "$stage" && test ! -L "$stage" || fail "RAM installer is not staged"
grep -q "^tmpfs $stage tmpfs .*nodev.*noexec" /proc/mounts ||
    fail "installer staging is not the guarded tmpfs"
grep -q "^/dev/sda34 $root ext4 " /proc/mounts ||
    fail "linuxroot is not mounted at the accepted path"
test ! -L "$root" || fail "linuxroot mount path is a symlink"

# Prevent the recovery-host supervisors from respawning services while the
# chroot is being drained. Never signal a process outside this exact root.
touch /run/t630-stopping
for proc in /proc/[0-9]*; do
    if [ "$(readlink "$proc/root" 2>/dev/null || true)" = "$root" ]; then
        kill -TERM "${proc##*/}" 2>/dev/null || true
    fi
done

attempt=0
while :; do
    remaining=0
    for proc in /proc/[0-9]*; do
        if [ "$(readlink "$proc/root" 2>/dev/null || true)" = "$root" ]; then
            remaining=1
        fi
    done
    [ "$remaining" = 1 ] || break
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        fail "Ubuntu processes are still exiting"
    fi
    sleep 1
done
sync

# Unmount children deepest-first without lazy or forced unmounts. Repeat after
# every successful pass because a parent may become visible only afterward.
while :; do
    children=$(awk -v root="$root/" '$2 ~ "^" root { print $2 }' /proc/mounts |
        sort -r)
    [ -n "$children" ] || break
    progress=0
    for target in $children; do
        if umount "$target"; then
            progress=1
        fi
    done
    [ "$progress" = 1 ] || fail "a linuxroot child mount is still busy"
done

umount "$root" || fail "linuxroot is still busy"
sync
if awk '$3 == "259:18" { found=1 } END { exit found ? 0 : 1 }' \
        /proc/self/mountinfo; then
    fail "linuxroot remains mounted"
fi
test -d "$stage" || fail "RAM installer disappeared"
echo INSTALLER_PREPARE_COMPLETE_LINUXROOT_UNMOUNTED_RAM_PRESERVED
