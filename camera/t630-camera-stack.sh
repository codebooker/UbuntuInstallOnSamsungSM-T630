#!/bin/bash
# Start the minimum Android services needed by Samsung's stock camera HAL.
set -eu

preload=/dev/t630-android-property-seed.so
pids=""

start_android_service() {
    output=$1
    shift
    env LD_PRELOAD="$preload" "$@" >"$output" 2>&1 &
    pids="$! $pids"
}

stop_services() {
    kill $pids 2>/dev/null || true
    wait $pids 2>/dev/null || true
}

trap stop_services EXIT INT TERM
for name in cameraserver servicemanager hwservicemanager; do
    if pgrep -x "$name" >/dev/null; then
        echo "Refusing to replace an existing $name process" >&2
        exit 1
    fi
done
: > /run/t630-android-log.txt

# Android's liblog writes binary datagrams to logdw. Capture them in the
# isolated runtime so failed HAL requests are diagnosable without logd.
if command -v /usr/local/sbin/t630-android-log-capture >/dev/null 2>&1; then
    /usr/local/sbin/t630-android-log-capture >/run/t630-log-capture.out 2>&1 &
    pids="$! $pids"
    sleep 1
fi

start_android_service /run/t630-servicemanager.out /system/bin/servicemanager
start_android_service /run/t630-hwservicemanager.out /system/bin/hwservicemanager
sleep 2
env LD_LIBRARY_PATH=/system/lib64:/system/lib64/bootstrap:/apex/com.android.i18n/lib64 \
    LD_PRELOAD="$preload" /data/vendor/camera/t630-binder-placeholder \
    SurfaceFlingerAIDL android.gui.ISurfaceComposer \
    >/run/t630-surfaceflinger-placeholder.out 2>&1 &
pids="$! $pids"
sleep 1
start_android_service /run/t630-display-allocator.out \
    /vendor/bin/hw/vendor.qti.hardware.display.allocator-service
sleep 2
start_android_service /run/t630-camera-provider.out \
    /vendor/bin/hw/vendor.samsung.hardware.camera.provider@4.0-service_64
sleep 24
start_android_service /run/t630-cameraserver.out /system/bin/cameraserver
attempt=0
until timeout 8 env LD_PRELOAD="$preload" /system/bin/cmd media.camera help \
        2>/dev/null | grep -q 'set-watchdog'; do
    attempt=$((attempt + 1))
    test "$attempt" -lt 20
    sleep 1
done

# There is no tombstoned/system_server in this hybrid runtime. A timed-out HAL
# call must return an ordinary error, not ask Android's watchdog to abort the
# compatibility stack (and with it the surrounding Ubuntu userspace).
timeout 8 env LD_PRELOAD="$preload" /system/bin/cmd media.camera \
    set-watchdog 0 >/run/t630-camera-watchdog.out 2>&1
test ! -s /run/t630-camera-watchdog.out
sleep 2
touch /run/t630-camera-ready

while :; do
    sleep 3600 &
    wait $!
done
