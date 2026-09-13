set -e
mkdir -p /run/ubuntu/run/dbus
chroot /run/ubuntu dbus-uuidgen --ensure
if ! test -S /run/ubuntu/run/dbus/system_bus_socket; then
  chroot /run/ubuntu dbus-daemon --system --fork
fi
chroot /run/ubuntu /usr/bin/nohup /usr/sbin/NetworkManager --no-daemon </dev/null >/run/network-manager.log 2>&1 &
sleep 3
chroot /run/ubuntu nmcli -t -f DEVICE,TYPE,STATE device
chroot /run/ubuntu iw dev
