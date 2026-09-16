# CNSS filesystem-ready acceptance (2026-09-16)

> **Superseded for normal startup.** The fast path below passed a normal reboot,
> but later full Power Off testing exposed a Samsung charger/LPM-only kernel
> panic on the first scan. Normal startup no longer sends the filesystem-ready
> shortcut and uses the stock timeout. Boot v12 first converts charger/LPM boot
> into a normal boot. See
> [the corrective report](cold-boot-wlan-charger-guard-20260916.md).

## Problem

The stock WCN6850 stack previously loaded `cnss2` and `qca_cld3_wlan`
consecutively. Samsung's CNSS driver requires its normal filesystem-ready event
between those steps to start cold-boot calibration. Without it, WLAN driver
registration waited for a 70,000 ms calibration timeout and Wi-Fi typically
connected around 80 seconds after boot.

## Guarded integration

`signal-wifi-filesystem-ready` is now embedded in the persistent boot ramdisk.
Before writing the exact CNSS `fs_ready` attribute, it pins and validates:

- root privilege, SM-T630 model, DZE3 kernel release, and install identity;
- the fixed selected Ubuntu root;
- loaded `cnss2` and an absent `wlan` module;
- the exact `b0000000.qcom,cnss-qca6490` platform and CBC property;
- the `/run/input-firmware` firmware-class path; and
- required nonempty QCA6490 firmware, board-data, and WLAN configuration files.

The helper emits the driver's ordinary filesystem-ready event. It does not
forge calibration completion, MAC data, regulatory data, or module state. The
startup path then loads `qca_cld3_wlan`. If any guard rejects the event, startup
still loads WLAN and retains the known-working slow timeout path.

## Boot candidate and write boundary

The reproducible v7 candidate kept the accepted module-compatible kernel:

- kernel SHA-256: `7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6`
- boot SHA-256: `83a3eb1ea8a63df4989bb893d14f525b60c43bbf4b1d7ae2574e641d6811f1cd`
- ramdisk SHA-256: `3b9208836b72a8cb8002f206e67338b4b7798a6cdbfc8c5084a7bfddc06aad98`

The writer accepted only the exact installed v6 hash, battery/power state,
unmounted 96 MiB BOOT partition, model, kernel, and candidate hash. It wrote
only `/dev/sda19`, verified the full readback, and verified that `dtbo`,
`vendor_boot`, `init_boot`, and `vbmeta` were unchanged.

## Physical result

The orderly restart retained the personalized clean root. Observed milestones:

- filesystem-ready accepted: 3.77 seconds;
- CNSS entered calibration: 14.96 seconds;
- firmware calibration-done indication: 19.55 seconds;
- WLAN module load returned: 20.83 seconds;
- network association began: about 25.6 seconds; and
- DHCP acknowledgment: about 27.7 seconds.

There was no 70,000 ms timeout. `wlan0` reconnected to the saved network, the
owner-only SSH service accepted its pinned key, and a real HTTPS request returned
HTTP 200. Weston, GNOME, Bluetooth, the speaker sink, microphone source,
accelerometer, touchscreen, and S Pen palm guard all returned. The boot contained
zero matching kernel panic, Oops, KGSL fault, watchdog, or video-overload markers.

The complete repository suite then passed 326 tests with five expected
environment-dependent skips.
