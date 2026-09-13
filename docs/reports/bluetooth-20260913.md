# SM-T630 Bluetooth bring-up — 2026-09-13

## Result

The Galaxy Tab Active4 Pro's WCN6850 Bluetooth controller now works under the
native Ubuntu installation through BlueZ and GNOME. The verified boot image is
`output/bluetooth-rxd-wakeup-v7/boot.img`, SHA256
`c9fd8a0025e2c8acc8c7781a077c2af71eb49c01688cf9ae010a4bc8c15118db`.
The boot partition readback matched and the guarded writer verified that
`sda20`, `sda21`, `sda22` and `sde19` were unchanged.

## Root causes and fixes

Samsung's stock kernel disabled HCI UART, while the controller requires a
Samsung/QTI firmware download, board NVM overrides and Qualcomm in-band sleep.
The exact DZE3 kernel was rebuilt with HCI UART/QCA support. The userspace loader
downloads the stock WCN6850 patch and board calibration at 3.2 Mbps, then hands
the live UART to the QCA line discipline.

The upstream QCA driver sent `IBS_WAKE_IND` directly. Samsung's exact QTI HAL
instead performs a receiver-wake pulse first: RTS low, 38400 baud without
hardware flow control, one zero byte, normal UART settings restored, RTS high,
then `IBS_WAKE_IND`. The board-scoped kernel patch reproduces that sequence.

The controller can still miss Linux's first `Write LE Host Supported` command
while settling after firmware handoff. HCI initialization recovers, and the
startup launcher now retries the standard command, verifies its exact successful
completion, and only then launches BlueZ. A redundant `btmgmt info` check was
removed because that utility remains attached as a monitor after printing its
answer. The launcher also handles a transient D-Bus-activated `bluetoothd`
without waiting forever on the UART owner.

## Physical verification

Clean boot `79fdbd99-b920-459c-bd1f-ee2886e431b0` established all of the
following:

- BlueZ, GNOME, Wi-Fi and SSH started automatically.
- The adapter reported powered, SSP, BR/EDR, LE and secure connections.
- Correct HCI replies arrived after 5, 10 and 30 seconds of controller idle.
- A direct management scan completed with 52 discovery events.
- Two sustained BlueZ scans completed normally; the first created 16 D-Bus
  device objects and the second raised the retained total to 20.
- No Bluetooth timeout was logged after the single recovered boot-time LE-host
  miss. No Bluetooth addresses are recorded here.

The remaining early timeout is visible but no longer functional: the verified
retry completes before BlueZ starts. Future work can move the retry into a
kernel delayed-init path if eliminating that benign log line becomes valuable.
