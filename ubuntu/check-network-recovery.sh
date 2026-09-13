#!/bin/sh
# Collect network recovery diagnostics without embedding a private SSID.
set -eu

connection=${1:-}

chroot /run/ubuntu /bin/sh -s -- "$connection" <<'EOF'
nmcli -f DEVICE,TYPE,STATE,CONNECTION device
if [ -n "$1" ]; then
    nmcli -f connection.id,connection.interface-name,connection.autoconnect,802-11-wireless.mac-address connection show "$1"
fi
ip -br link
ls /etc/systemd/network /etc/udev/rules.d
cat /etc/NetworkManager/dispatcher.d/90-t630-remote
pgrep -a NetworkManager
tail -40 /var/log/t630-networkmanager.log
ls /run/*etwork* /var/log/*etwork*
EOF
dmesg | tail -40
