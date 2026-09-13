#!/bin/busybox sh
grep '/run/ubuntu' /proc/self/mountinfo
for p in /proc/[0-9]*; do
    root=$(readlink "$p/root" 2>/dev/null || true)
    cwd=$(readlink "$p/cwd" 2>/dev/null || true)
    case "$root:$cwd" in
        *'/run/ubuntu'*)
            echo "PID=${p##*/} ROOT=$root CWD=$cwd"
            tr '\000' ' ' <"$p/cmdline"; echo
            ;;
    esac
done
chroot /run/ubuntu /usr/bin/fuser -vm /dev 2>&1 || true
