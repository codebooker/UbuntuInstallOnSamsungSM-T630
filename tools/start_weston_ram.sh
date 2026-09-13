set -e
mkdir -p /run/ubuntu/run/user/0 /run/ubuntu/run/udev
chmod 700 /run/ubuntu/run/user/0
chroot /run/ubuntu /usr/bin/nohup /usr/lib/systemd/systemd-udevd --daemon </dev/null >/run/udevd-launch.log 2>&1
chroot /run/ubuntu udevadm trigger --subsystem-match=drm --action=add
chroot /run/ubuntu udevadm trigger --subsystem-match=input --action=add
chroot /run/ubuntu udevadm settle --timeout=5 || true
chroot /run/ubuntu /usr/bin/env SEATD_VTBOUND=0 /usr/bin/nohup /usr/sbin/seatd -l debug </dev/null >/run/seatd.log 2>&1 &
sleep 1
chroot /run/ubuntu /usr/bin/env HOME=/root XDG_RUNTIME_DIR=/run/user/0 LIBSEAT_BACKEND=seatd SEATD_VTBOUND=0 /usr/bin/nohup /usr/bin/weston --backend=drm-backend.so --renderer=pixman --config=/tmp/t630-weston.ini --log=/tmp/weston.log --socket=wayland-0 </dev/null >/run/weston-launch.log 2>&1 &
sleep 3
cat /run/weston-launch.log
cat /run/ubuntu/tmp/weston.log
cat /run/seatd.log
