# Correct signed IPA firmware and power retry loop

## Cause and live proof

The built-in IPA driver attempted to load `yupik_ipa_fws` every approximately
512ms. The related Samsung SM7325 [driver source](https://github.com/Mesa-Labs-Archive/android_kernel_samsung_sm7325/blob/sep-15/stock/techpack/dataipa/drivers/platform/msm/ipa/ipa_v3/ipa.c)
has a 500ms delayed retry on firmware-load failure and no platform remove
callback. No live unbind/unload was attempted.

The vendor filesystem copy passes ELF structure/memory-range checks but fails
the secure loader's image initialization with EINVAL. A four-second controlled
test confirmed this. Its temporary links were removed, with no partition
writes and no changes to audio calibration or security policy.

Stock fstab instead mounts APNHLOS at `/vendor/firmware_mnt`. The exact partition
was resolved using `/sys/class/block/sda23/uevent` (PARTNAME=apnhlos), probed as
FAT, and mounted **read-only, nodev, nosuid, noexec**. Its `image/yupik_ipa_fws.*`
files have identical executable segments and header to the vendor copy, but
different signing data (`b01`) and combined metadata (`mdt`).

Signed metadata SHA256:
`f92680638f8702f45e7d2a183abe818a3a7f80b6ffbbe3f8563414589f30ae86`.
Vendor metadata SHA256:
`30b84e0259e3b893f8227cd24c334f63863b75ab628ef34d6b56aa9e852d9e53`.

The signed copy loaded successfully at old-boot uptime11601s:
`Brought out of reset`, `IPA FW loaded successfully`, subsystem ONLINE.
The repeated firmware failures stopped. Existing `qrtr_ws` event counter49603
remained unchanged across subsequent checks, unlike its prior twice-per-second
activity. Wi-Fi SSH and the normal speaker sink remained available. This fixes
an observed background retry/wakeup source, not yet proof of reliable suspend
or a measured battery-life improvement.

## Installed and recovery

Six validated files copied into `/opt/t630/ipa-firmware`, root-owned0644; original
vendor files and APNHLOS remain untouched. Temporary stock mount was unmounted.
`/usr/local/sbin/t630-ipa-start` validates every SHA256 and the exact device/kernel,
then creates only those six firmware links in both caller roots (metadata last).
It refuses unexpected files/links and waits at most80seconds for ONLINE.

The existing desktop-autostart hook launches this helper independently in the
background; a firmware failure cannot block GNOME, audio or recovery. Opt-out:
`/etc/t630/ipa.disabled`. Prior desktop-autostart backup:
`/usr/local/share/t630/backups/ipa-firmware.ahDvFY`.

Four isolated validation tests pass: accepted fixture/order, wrong signing,
missing file, and symlink-source rejection. Python compilation and autostart
shell syntax checks passed. Live helper validation and desktop `--check` passed.

A clean reboot was dispatched using the previously verified unmount-first
shutdown helper. New boot ID: `fd8bcf77-e2ef-4405-993b-0b7928404b79`.
At42seconds GNOME startup lock was verified and firmware links staged; the first
kernel firmware request was still in its existing early-boot fallback timeout.
Final startup validation follows below.

## Cold-boot result

IPA reached ONLINE at uptime62.988s. The kernel's first request, made before
Ubuntu staged its files, still waited for its existing60-second fallback timeout;
the next retry loaded the signed copy successfully and no further retry loop
appeared. GNOME startup password lock, Wi-Fi SSH/[redacted Wi-Fi network], audio-ready flag, normal
PipeWire speaker sink and charging all returned. All four firmware-validation
tests also passed on the tablet. Brightness83/idle300 preferences remained intact.

## Wi-Fi wake-rule follow-up

The related SM7325 [suspend callback](https://github.com/LineageOS/android_kernel_samsung_sm7325/blob/lineage-23.2/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_power.c)
accepts a cfg80211 wow argument but does not apply its pattern list. This explains
why `iw` readback alone did not verify the firmware's actual wake filters.
The [vendor WoWL interface](https://github.com/LineageOS/android_kernel_samsung_sm7325/blob/lineage-23.2/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_wowl.c)
adds patterns through PMO and can remove an exact pattern string afterward.

`test-t630-driver-wake-pattern.py` first tried an Ethernet-WoL14-byte pattern;
the actual sysfs parser rejected the39-character command before installation
because it allows only32bytes. A21-character unicast-destination-only pattern
was accepted and removed successfully. It matches this tablet's MAC and excludes
broadcasts while still permitting directed traffic to wake it. No persistent
Wi-Fi policy change. Actual timed freeze with the vendor pattern awaits unplug.
The sleep test now records RTC interrupt delta and BOOTTIME-minus-MONOTONIC,
instead of trusting a potentially stale kernel timekeeping message alone.
