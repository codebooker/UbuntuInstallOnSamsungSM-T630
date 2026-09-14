# SPI sysfs `name` panic (2026-09-14)

During the read-only optional-hardware inventory, reading
`/sys/bus/spi/devices/spi0.0/name` with `head` reproduced the downstream
kernel's known generic device-name crash. No NFC module had been loaded and no
hardware setting was changed.

The preserved previous-boot log records:

- previous uptime: 1116.63 seconds
- reader process: `head`, PID 26486
- null dereference address: `0x20`
- fault PC: `name_show+0x20/0x58`
- call path: `dev_attr_show`, `sysfs_kf_seq_show`, `kernfs_seq_show`, `seq_read`
- final result: fatal exception and kernel panic

The tablet rebooted normally into boot ID
`79940f92-cb0d-461f-9234-261fd0549b8f`. Weston, GNOME, Wi-Fi, Bluetooth,
audio, and the accelerometer passed the post-reboot runtime check. The camera
vendor stack was off, `nfc_sec` remained unloaded, and the new boot contained
no kernel-fault marker.

This expands the existing diagnostic prohibition. It is not sufficient to
avoid only recursive `/sys` searches: generic `name` attributes on unfamiliar
bus devices must also be treated as unsafe. Runtime tools may read only exact,
previously validated sysfs paths. Identity discovery should prefer `uevent`,
`modalias`, driver symlinks, and device-tree `compatible` properties, and even
those should be accessed only for a narrowly selected device.
