#!/bin/busybox sh
cat /proc/sys/kernel/random/boot_id
cat /proc/uptime
cat /run/t630-gnome-reboot.log 2>/dev/null || true
grep '/run/ubuntu' /proc/mounts
ps | grep -E 'weston|gnome|NetworkManager|start-ubuntu' | head -n 20
tail -n 15 /run/ubuntu/run/t630-gnome-autostart.log 2>/dev/null || true
tail -n 10 /run/network.log 2>/dev/null || true
