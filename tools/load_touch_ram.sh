set -e
test -d /run/stock-vendor/firmware/tsp_stm
# Alias only the read-only RAM copy, never the internal vendor partition.
test -e /vendor || ln -s /run/stock-vendor /vendor
printf '%s' /run/stock-vendor/firmware > /sys/module/firmware_class/parameters/path
for module in sec_tsp_log sec_cmd sec_common_fn sec_secure_touch sec_tclm_v2 sec_tsp_dumpkey stm_ts_fts1b90a w9019; do
  if test -d "/sys/module/$module"; then
    echo "Already loaded: $module"
  else
    echo "Loading matching stock module: $module"
    insmod "/run/stock-vendor/lib/modules/$module.ko"
  fi
done
mdev -s
cat /proc/bus/input/devices
dmesg | tail -90
