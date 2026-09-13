ls -l /dev/dri /dev/card0 /dev/renderD128 /run/ubuntu/dev/dri /run/ubuntu/dev/card0 2>/dev/null
echo SYSFS
cat /sys/class/drm/card0/dev /sys/class/drm/card0/uevent
echo MODETEST_HELP
chroot /run/ubuntu /usr/bin/modetest -h
