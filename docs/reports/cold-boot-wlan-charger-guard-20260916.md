# Cold-boot WLAN and charger-mode acceptance (2026-09-16)

## Failure isolated

Orderly restart worked, but full Power Off while USB-powered repeatedly reset
the first personalized boot and then entered the one-shot fallback root. The
persistent boot journal proved that the release selector was correctly rearmed,
consumed, and reached `startup-dispatched`; the failure was after userspace
startup, not in root selection.

`/proc/last_kmsg` preserved the fault. The first WLAN scan queued regulatory
beacon work and dereferenced address `0x14`:

```text
Workqueue: events reg_todo
pc : handle_reg_beacon+0xb0/0x148
lr : reg_todo+0x720/0x7f4
Kernel panic - not syncing: Fatal exception in interrupt
```

Five-second userspace gating moved the panic from about 21.7 to 27.2 seconds.
Restoring the stock CNSS timeout moved it to about 76.8 seconds. Neither timing
change corrected the invalid regulatory state.

The decisive difference was the kernel command line. USB-powered cold startup
contained `androidboot.mode=charger`, `androidboot.baseband=lpm`, and
`sec_mparam.lpcharge=1`. In that boot the stock kernel logged that cfg80211
regulatory initialization was skipped because of LPM mode. After the panic,
Samsung rebooted normally; cfg80211 initialized and the fallback root survived.

An independent userspace bug was also removed. The personalized Netplan profile
had `match: {}`, so NetworkManager could attach it to `swlan0` or a renamed P2P
interface. The stable profile was MAC-bound to the real `wlan0` client. Both the
first-boot wizard and the later Wi-Fi helper now prefer `wlan0`, reject Samsung's
secondary/P2P names as fallbacks, and persist the selected radio's hardware
address in the NetworkManager profile. No device address is embedded in source
or release packages.

## Guarded fix

The persistent initramfs now detects Samsung charger/LPM command-line state
after establishing the independent USB recovery console. It performs a clean
forced reboot before `start-ubuntu` runs, so the release-root selector is not
consumed and WLAN is never loaded with cfg80211 disabled. The next boot is a
normal boot and consumes the selector once as intended.

Normal WLAN startup also retains the stock driver's bounded CNSS timeout. The
filesystem-ready helper remains available for diagnosis but is no longer called
by the boot path.

## Candidate and physical acceptance

Boot v12 retained the exact accepted kernel:

- kernel SHA-256: `7ffa08471df8e47cf9d6cccca55ff24c96e3afc8393f4163ef0a020f7d2958b6`
- boot SHA-256: `a7bde8259ab09b8238e0a1c8871e94422c3a6eb29e95ff8218e2de1746cd2e28`
- ramdisk SHA-256: `6a90ee755d160d97ff9c3d8583406e5d249c627217608be13c4a6ce60f3267bc`

The image rebuilt byte-for-byte, passed AVB verification, wrote only the exact
96 MiB BOOT partition, matched full readback, and left `dtbo`, `vendor_boot`,
`init_boot`, and `vbmeta` at their pinned hashes.

Physical acceptance powered the tablet fully off while it remained connected to
USB. The charger/LPM pass rebooted before Ubuntu, the next command line was
normal, and the personalized root—not the fallback—reached
`startup-dispatched`. GNOME was running before WLAN completed. The WLAN module
returned at 75.84 seconds, NetworkManager connected `wlan0`, `swlan0` remained
disconnected, and the tablet stayed on the personalized root beyond the prior
failure point.

The final read-only health check reported Weston and GNOME running, Wi-Fi
connected on `wlan0`, Bluetooth powered with audio roles, the calibrated speaker
sink and microphone source, valid device permissions, battery reporting,
accelerometer availability, and zero kernel fault markers. The refreshed live
package set passes `dpkg --audit` and `apt-get check` under
`t630-release-base` 0.1.15.
