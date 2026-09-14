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
| NFC | `CONFIG_NFC_FEATURE_SN100U`, `CONFIG_NFC_PN547`, `CONFIG_SAMSUNG_NFC=m`; matching `nfc_sec.ko` retained | Kernel and vendor module sources are present. The module was not active and no NFC device node existed; safe load/service work and a physical tag test remain. |
| GNSS/GPS | `CONFIG_GNSS=y` | The generic kernel framework is present, but no GNSS device node or userspace provider was exposed. Vendor transport/firmware identification remains. |

## Release tests still required

1. Insert a disposable microSD card; verify detection, mount, write, unmount and
   suspend/resume without touching internal partitions.
2. Use a powered USB-C hub with a keyboard and disposable flash drive; verify
   host-role negotiation, hotplug and clean unmount.
3. Connect a USB-C DisplayPort adapter and monitor; verify mode enumeration,
   mirroring/extension, rotation behavior and disconnect recovery.
4. Bring up the exact Samsung NFC module only after its device-tree, firmware,
   node permissions and shutdown behavior are audited; then test a passive tag.
5. Identify the stock GNSS service/transport and proprietary dependencies before
   starting it; verify a cold fix outdoors without writing Android calibration
   partitions.
