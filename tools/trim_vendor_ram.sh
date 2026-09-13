set -e
test ! -e /run/vendor-minimal
test "$(readlink /vendor)" = /run/stock-vendor
mkdir -p /run/vendor-minimal/lib
cp -a /run/stock-vendor/firmware /run/vendor-minimal/
cp -a /run/stock-vendor/lib/modules /run/vendor-minimal/lib/
cp -a /run/stock-vendor/etc /run/vendor-minimal/
printf '%s' /run/vendor-minimal/firmware > /sys/module/firmware_class/parameters/path
ln -sfn /run/vendor-minimal /vendor
umount /run/stock-vendor
# This is our extracted temporary RAM image, still preserved on the Mac.
rm /run/stock-vendor.img
df -h /run
free -m
