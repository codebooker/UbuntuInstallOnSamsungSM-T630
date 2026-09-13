set -e
chroot /run/ubuntu /usr/bin/pkill -TERM -x NetworkManager
chroot /run/ubuntu /usr/bin/pkill -TERM -x dbus-daemon
sleep 1
# Remove only the PID/socket belonging to the RAM-only bus just stopped.
test ! -e /run/ubuntu/run/dbus/pid || rm /run/ubuntu/run/dbus/pid
test ! -S /run/ubuntu/run/dbus/system_bus_socket || rm /run/ubuntu/run/dbus/system_bus_socket
chroot /run/ubuntu /usr/bin/nohup /usr/bin/dbus-daemon --system --nofork --nopidfile </dev/null >/run/dbus-system.log 2>&1 &
sleep 1
chroot /run/ubuntu /usr/bin/nohup /usr/sbin/wpa_supplicant -u -s </dev/null >/run/wpa-supplicant.log 2>&1 &
chroot /run/ubuntu /usr/bin/nohup /usr/sbin/NetworkManager --no-daemon --log-level=DEBUG --log-domains=CORE,DEVICE,WIFI,SUPPLICANT </dev/null >/run/network-manager2.log 2>&1 &
sleep 2
chroot /run/ubuntu /usr/bin/nmcli general status
chroot /run/ubuntu /usr/bin/nmcli -f DEVICE,TYPE,STATE device
cat /run/dbus-system.log
