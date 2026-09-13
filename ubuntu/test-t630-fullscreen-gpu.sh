#!/bin/sh
# One live GPU session with the ordinary software launcher on failure.
# Does not change next-boot renderer policy or terminate any existing session.
set -eu
test "$(id -u)" = 0
test "$(cat /etc/t630-install-id)" = SM-T630-T630XXSBDZE3-Ubuntu-v1
test -f /etc/t630/gpu.disabled
test -f /etc/t630/gpu-sysmem.enabled
test -f /etc/t630/lock-on-start
test -f /etc/t630/login.enabled
test ! -e /tmp/.X11-unix/X3
if /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 HOME=/root T630_GNOME_FULLSCREEN=1 T630_GPU_RENDERER=1 \
    T630_MANAGED_SESSION=1 /usr/local/bin/t630-gnome-preview; then
    exit 0
fi
echo 'Live GPU trial failed; starting the software-rendered password-locked desktop.'
exec /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 HOME=/root T630_GNOME_FULLSCREEN=1 T630_GPU_RENDERER=0 \
    T630_MANAGED_SESSION=1 /usr/local/bin/t630-gnome-preview
