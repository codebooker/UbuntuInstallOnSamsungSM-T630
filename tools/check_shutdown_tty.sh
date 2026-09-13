#!/bin/busybox sh
for fd in /proc/1051/fdinfo/*; do
    echo "$fd"
    grep '^mnt_id:' "$fd"
done
umount /run/ubuntu/dev
echo "unmount_dev=$?"
grep '/run/ubuntu' /proc/mounts
