set -e
chroot /run/ubuntu gcc -Wall -Wextra -Werror -shared -fPIC -O2 -I/usr/include/libdrm -o /tmp/t630-drm-compat.so /tmp/t630-drm-compat.c -ldl
chroot /run/ubuntu env SYSTEMD_IGNORE_CHROOT=1 udevadm trigger --subsystem-match=drm --action=add
chroot /run/ubuntu env SYSTEMD_IGNORE_CHROOT=1 udevadm trigger --subsystem-match=input --action=add
chroot /run/ubuntu env SYSTEMD_IGNORE_CHROOT=1 udevadm settle --timeout=5 || true
chroot /run/ubuntu env HOME=/root XDG_RUNTIME_DIR=/run/user/0 LIBSEAT_BACKEND=seatd LD_PRELOAD=/tmp/t630-drm-compat.so WESTON_DISABLE_GBM_MODIFIERS=1 /usr/bin/nohup weston --backend=drm-backend.so --renderer=pixman --config=/tmp/t630-weston.ini --log=/tmp/weston-compat.log --socket=wayland-0 </dev/null >/run/weston-compat-launch.log 2>&1 &
sleep 3
cat /run/weston-compat-launch.log
cat /run/ubuntu/tmp/weston-compat.log
