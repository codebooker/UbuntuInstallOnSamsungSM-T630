#!/bin/busybox sh
ps
for p in /proc/[0-9]*; do
    for fd in "$p"/fd/*; do
        target=$(readlink "$fd" 2>/dev/null || true)
        case "$target" in
            /run/ubuntu/*)
                echo "$fd -> $target"
                grep '^mnt_id:' "$p/fdinfo/${fd##*/}" 2>/dev/null || true
                ;;
        esac
    done
done
ls -l /proc/1051/fd
