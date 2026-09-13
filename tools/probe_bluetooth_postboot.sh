echo UPTIME
cat /proc/uptime
echo MOUNTS
grep /run/ubuntu /proc/mounts || true
echo PROCESSES
ps | grep -E 't630_qca_bt|bluetoothd|t630-bluetooth|NetworkManager|wpa_supplicant' | grep -v grep || true
echo RFKILL
for x in /sys/class/rfkill/rfkill*; do
    test -e "$x/type" || continue
    printf '%s type=' "$x"
    cat "$x/type"
    printf ' state='
    cat "$x/state" 2>/dev/null || true
done
echo HCI
ls -la /sys/class/bluetooth 2>/dev/null || true
echo AUTOSTART_LOG
tail -100 /run/ubuntu/run/t630-gnome-autostart.log 2>/dev/null || true
echo LOADER_LOG
tail -120 /run/ubuntu/var/log/t630-bluetooth-loader.log 2>/dev/null || true
echo START_LOG
tail -120 /run/ubuntu/var/log/t630-bluetooth-start.log 2>/dev/null || true
echo WIFI
ip -br link 2>/dev/null || true
echo DMESG
dmesg | grep -Ei 'Bluetooth|hci_uart|ttyHS0|bt_power|cnss|wlan' | tail -160
