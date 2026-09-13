set -e
test ! -e /run/ubuntu/opt/t630
mkdir -p /run/ubuntu/opt/t630 /run/ubuntu/root/.config /run/ubuntu/usr/local/lib /run/ubuntu/usr/local/bin
cp -a /run/vendor-minimal /run/ubuntu/opt/t630/vendor
cp /run/ubuntu/tmp/t630-drm-compat-v3.so /run/ubuntu/usr/local/lib/t630-drm-compat.so
cp /run/ubuntu/tmp/t630-drm-compat-v3.c /run/ubuntu/opt/t630/t630-drm-compat.c
cp /run/ubuntu/tmp/t630-weston-input.ini /run/ubuntu/root/.config/weston.ini
cp /run/ubuntu/tmp/connect_wifi.py /run/ubuntu/usr/local/bin/t630-connect-wifi
chmod 755 /run/ubuntu/usr/local/bin/t630-connect-wifi
chmod 755 /run/ubuntu /run/ubuntu/opt /run/ubuntu/opt/t630 /run/ubuntu/usr/local/lib /run/ubuntu/usr/local/bin
chroot /run/ubuntu /usr/bin/dpkg --audit
# Credential directories and all transient input/log files are excluded.
# No internal partition, /proc, /sys or /dev is included in this userspace snapshot.
chroot /run/ubuntu /usr/bin/nohup /bin/sh -c 'tar --one-file-system -czf /tmp/desktop-snapshot.tar.gz --exclude=./dev --exclude=./proc --exclude=./sys --exclude=./run --exclude=./tmp --exclude=./var/cache/apt/archives --exclude=./var/lib/apt/lists --exclude=./var/log --exclude=./etc/netplan --exclude=./etc/NetworkManager/system-connections --exclude=./var/lib/NetworkManager --exclude=./root/.bash_history -C / . > /tmp/snapshot.log 2>&1; echo $? > /tmp/snapshot.exit' </dev/null >/run/snapshot-launch.log 2>&1 &
