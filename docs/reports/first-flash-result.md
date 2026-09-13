# First experimental flash — 2026-09-12

Owner explicitly approved after being told the test could irreversibly trip
Knox, fail to boot, and require a stock restore/wipe, with restore untested.

Heimdall v2.2.2 ran a resumed session with only BOOT and VBMETA specified.
No repartition, PIT upload or size-check bypass was requested.

- BOOT: boot-test.img, 100663296 bytes,
  SHA256 596292caf0365d3f790bc205bdfca3cfaca9d7033d472e863a83bb883b833ea7.
- VBMETA: vbmeta-test.img, 65536 bytes,
  SHA256 a36c6c50bf35438c6ab20fb8d1b7630c1cbda8c272dfdda3abcce2082890e225.
- Both uploads reported successful; overall command exited 0.
- Tool ended the session and requested a reboot.
- Empty-bulk-transfer warnings occurred but did not prevent successful
  protocol completion. Complete output is in first-flash.log.

At 05:28:54 UTC the Mac had no tablet USB device, no diagnostic serial port,
and no ADB device. This is an initial observation, not a boot failure diagnosis.
Post-flash Knox state has not been measured. Waiting for boot/USB evidence
and the owner's report of the screen.

## Successful native boot confirmed

By 05:29:34 UTC USB enumerated as VID:PID 1d6b:0104 with serial
T630BRINGUP001 and product SM-T630 RAM-only diagnostic console. macOS created
`/dev/cu.usbmodemT630BRINGUP0011`.

The serial shell replied with:

```
Linux t630-bringup 5.4.274-qgki-31225846-abT630XXSBDZE3 ... aarch64 GNU/Linux
uid=0(root) gid=0(root)
```

PID 1's actual command line is `/bin/busybox sh /init nohyp_uart`.
Mounts contain only rootfs, proc, sysfs, tmpfs, devpts and configfs;
no internal block-device filesystem is mounted.

Kernel log confirms:

```
[0.000000] [DEFEX] Device is unlocked and DEFEX will be disabled
[1.308213] Run /init as init process
[1.332274] T630_BRINGUP: custom Linux /init reached
[1.394764] T630_BRINGUP: USB ACM bound
```

Post-flash kernel command line now explicitly reports
`androidboot.warranty_bit=1` and `androidboot.verifiedbootstate=orange`.
The previously warned Knox trip has therefore been observed, not merely assumed.
Also contains `androidboot.kg=0x1`, stock DTBO index 2 and DTB index 0.

Owner reports the Samsung unofficial-software warning remains on the display.
Linux is already running behind that retained display: it is not a blocking
prompt in this observed boot. No framebuffer console is configured. DRM card0
and connectors exist; `/sys/class/graphics` does not. No display write attempted.

Saved evidence:

- first-boot-console.txt: initial root-shell transcript and mount list.
- native-boot-summary.txt: cmdline, PID1, partitions, DRM/input inventory,
  startup log, uptime (135.92 seconds at capture).
- native-boot-dmesg.txt: 394143 bytes.
- native-boot-fdt.dtb: live flattened hardware description, 645679 bytes;
  valid DTB v17 magic/size as identified by `file`.

There was no additional flash, repartition, rootfs installation or storage
mount. Restoring Android remains untested. The first native Linux boot
milestone is achieved; Ubuntu userspace and graphical hardware bring-up are
separate next milestones.
