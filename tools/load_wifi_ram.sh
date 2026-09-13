set -e
# Supply Wi-Fi files without exposing unrelated IPA firmware to its retry loop.
test -e /run/input-firmware/qca6490 || ln -s /run/vendor-minimal/firmware/qca6490 /run/input-firmware/qca6490
test -e /run/input-firmware/wlan || ln -s /run/vendor-minimal/firmware/wlan /run/input-firmware/wlan
for module in cnss_prealloc cnss_nl cnss_utils device_management_service_v01 wlan_firmware_service_v01 cnss2 qca_cld3_wlan; do
  if ! test -d "/sys/module/$module"; then
    echo "Loading $module"
    timeout 20 insmod "/run/vendor-minimal/lib/modules/$module.ko"
  fi
done
ls /sys/class/net
dmesg | tail -90
