# Optional hardware inventory (2026-09-14)

This is a non-destructive driver and connector inventory from the physical
SM-T630 running the verified DZE3-compatible kernel. It deliberately used only
explicit known sysfs paths; recursive sysfs probing is unsafe on this Samsung
kernel. Presence means the software path exists, not that an accessory has
passed a physical test.

## Results

| Area | Evidence | Current conclusion |
| --- | --- | --- |
| microSD | `CONFIG_MMC`, `CONFIG_MMC_BLOCK`, `CONFIG_MMC_SDHCI_MSM`; two MMC hosts | Controller support is present. No card/block device was inserted during inventory. |
| USB host | `CONFIG_USB_OTG`, `CONFIG_USB_ROLE_SWITCH`, `CONFIG_USB_XHCI_HCD`, DWC3 | Host support is present. The current cable negotiated sink/device mode, so a storage/HID host test remains. |
| USB-C display | DRM exposes `card0-DP-1`; Samsung DisplayPort options are enabled | DisplayPort support is present. Connector reported disconnected and no monitor modes, as expected without an adapter/display. |
| NFC | SN100 feature path using the `pn547` compatibility ABI at I2C bus 22/address `0x2b`; matching `nfc_sec.ko` and NXP/Samsung HIDL payload retained | The exact controller path is identified. Auto-load remains prohibited until the driver's incomplete unload/power teardown is corrected and the proprietary service has a bounded bridge. |
| GNSS/GPS | `CONFIG_GNSS=y`; Qualcomm GNSS 2.1 service, Samsung/Qualcomm HIDL libraries, location daemons, and configs retained | This is a proprietary HIDL/QMI integration rather than a missing `gpsd` package. Transport identification and an isolated GeoClue bridge remain. |

## Release tests still required

1. Insert a disposable microSD card; verify detection, mount, write, unmount and
   suspend/resume without touching internal partitions.
2. Use a powered USB-C hub with a keyboard and disposable flash drive; verify
   host-role negotiation, hotplug and clean unmount.
3. Connect a USB-C DisplayPort adapter and monitor; verify mode enumeration,
   mirroring/extension, rotation behavior and disconnect recovery.
4. Correct and test the exact Samsung NFC module's unload/power path, then add a
   bounded NXP/Samsung service bridge and test a passive tag.
5. Identify the Qualcomm GNSS transport and firmware nodes, then add an isolated
   GeoClue bridge and verify a cold fix outdoors without writing Android
   calibration partitions.

See [the detailed NFC/GNSS prerequisite audit](nfc-gnss-prerequisites-20260914.md)
before attempting either service.
