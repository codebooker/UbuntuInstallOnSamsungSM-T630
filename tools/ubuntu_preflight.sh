set -e
echo MEMORY
free -m
echo RAM_STORAGE
df -h /run
echo UBUNTU_STATE
ls -ld /run/ubuntu /run/ubuntu-base-24.04.5-arm64.tar.gz 2>/dev/null || true
echo DISPLAY
for c in /sys/class/drm/card0-*; do
  echo "$c"
  cat "$c/status" "$c/modes" 2>/dev/null || true
done
echo POWER
for p in /sys/class/power_supply/*; do
  echo "$p"
  cat "$p/type" "$p/status" "$p/capacity" "$p/temp" 2>/dev/null || true
done
