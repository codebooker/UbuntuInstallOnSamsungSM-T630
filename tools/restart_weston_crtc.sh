set -e
chroot /run/ubuntu gcc -Wall -Wextra -Werror -shared -fPIC -O2 -I/usr/include/libdrm -o /tmp/t630-drm-compat-v2.so /tmp/t630-drm-compat-v2.c -ldl
chroot /run/ubuntu pkill -TERM -x weston
sleep 1
chroot /run/ubuntu env HOME=/root XDG_RUNTIME_DIR=/run/user/0 LIBSEAT_BACKEND=seatd LD_PRELOAD=/tmp/t630-drm-compat-v2.so WESTON_DISABLE_GBM_MODIFIERS=1 /usr/bin/nohup weston --backend=drm-backend.so --renderer=pixman --config=/tmp/t630-weston.ini --log=/tmp/weston-crtc.log --socket=wayland-0 --debug </dev/null >/run/weston-crtc-launch.log 2>&1 &
sleep 3
cat /run/weston-crtc-launch.log
tail -45 /run/ubuntu/tmp/weston-crtc.log
