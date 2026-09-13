sleep 3
echo STATE
cat /sys/class/rfkill/rfkill0/state 2>/dev/null || true
ls -la /sys/class/bluetooth 2>/dev/null || true
echo PROCESSES
ps | grep -E 't630_qca_bt|bluetoothd|t630-bluetooth' | grep -v grep || true
echo LOADER
tail -50 /run/ubuntu/var/log/t630-bluetooth-loader.log 2>/dev/null || true
echo START
tail -30 /run/ubuntu/var/log/t630-bluetooth-start.log 2>/dev/null || true
echo HCICONFIG
chroot /run/ubuntu timeout 4 hciconfig -a 2>&1 || true
echo BTMGMT
chroot /run/ubuntu timeout 4 btmgmt info 2>&1 || true
echo DBUS
chroot /run/ubuntu timeout 4 busctl --system tree org.bluez 2>&1 || true
echo KERNEL
dmesg | grep -Ei 'Bluetooth|hci_uart|ttyHS0|bt_power' | tail -60
