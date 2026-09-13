# SM-T630 Wi-Fi SSH and physical-screen view — 2026-09-12

## Verified result

- Native Ubuntu SSH works at `TABLET_IP:22` from the Mac over [redacted Wi-Fi network] Wi-Fi.
- Dedicated Mac ED25519 key, root public-key login only. Password and interactive
  authentication are disabled; a connection with public-key authentication
  disabled was rejected with `Permission denied (publickey)`.
- Tablet ED25519 host public key was obtained through the existing USB serial
  connection and pinned before the first SSH login. Host-key fingerprint:
  `SHA256:BkqUcz7ZOOCwf9mbvEW69WSZQ1ICEKl5sCXAIGbqOJo`.
- The real DRM scanout is captured read-only, rotated to landscape and served
  as PNG. It shows the physical purple desktop and terminal, not another desktop.
  This is a periodically refreshed view-only feed, not interactive VNC.
- Screen service listens only on `127.0.0.1:8765` on the tablet. A LAN connection
  to `TABLET_IP:8765` was refused. Mac tunnel binds only `127.0.0.1:18765`.
- Screen HTML and PNG returned HTTP 200 through the SSH tunnel. Fresh PNG
  captured again after reconnect; initial image visually inspected.
- Actual auto-start test: stopped SSH listener and screen process, disconnected
  and reconnected wlan0 using the retained USB console. NetworkManager's real
  dispatcher restarted both services (new PIDs 1775 and 1777). A fresh SSH login
  and screen capture then succeeded. Repeated startup calls created no duplicates.
- Configured for Wi-Fi-up startup on subsequent boots; this particular change
  has not been cold-reboot-tested. No boot image was rewritten for remote access.
- Latest battery reading: 6%, Charging (up from 3% earlier). Backlight remains
  temporarily dimmed to 120/306 while charging.

## Use

Run from the project directory:

```sh
ssh -F port/ssh_config tablet
```

The current live browser view is `http://127.0.0.1:18765`. It requires the Mac's
SSH tunnel to remain running. To start a tunnel when none is listening there:

```sh
ssh -F port/ssh_config -N -L 127.0.0.1:18765:127.0.0.1:8765 -o ExitOnForwardFailure=yes tablet
```

The browser refreshes about every 1.5 seconds plus capture/transfer time and has
a Pause button. Capture runs only when requested. SSH remains available for
administration. USB is no longer needed for routine access on this LAN, but keep
USB serial as the fallback for Wi-Fi failure, recovery, and boot troubleshooting.
The tablet address is assigned by DHCP and may change; update the scoped config
and verify the existing pinned host key if it does. Do not disable host checking.

## Installed components

- Ubuntu packages: `openssh-server`, `python3-pil` and required dependencies.
- `/etc/ssh/sshd_config_t630`: dedicated configuration; only ED25519 host key,
  no password/keyboard-interactive login, no agent/X11/remote forwarding.
  Local TCP forwarding restricted to the screen service.
- `/root/.ssh/authorized_keys_t630`: dedicated public key, root:root mode 600;
  parent directory mode 700. Existing generic authorized_keys not replaced.
- `/usr/local/libexec/t630-capture`: read-only DRM capture, compiled natively
  from `/usr/local/share/t630/capture_scanout.c` with warnings treated as errors.
- `/usr/local/libexec/t630-screen`: Python/Pillow view-only HTTP service.
- `/usr/local/sbin/t630-remote-start`: validated, idempotent service startup.
- `/etc/NetworkManager/dispatcher.d/90-t630-remote`: starts on wlan0 up/DHCP change.
- `/usr/local/share/t630/stop-ubuntu`: extends existing clean-reboot helper to
  terminate SSH and screen processes before unmounting Ubuntu. Startup copies it
  into outer initramfs RAM only after checking the original or updated hash.
  Updated SHA256: `796b7aa10e4467d8d31187d95b89d7d0767f6c0c93eb82ebd2cb6633bf64b812`.
  Do not invoke shutdown directly from an attached SSH shell: use the USB console
  or a deliberately detached outer-initramfs command so session closure cannot
  interrupt cleanup. No reboot was performed for this setup.

Mac files: dedicated private key `$HOME/.ssh/t630_ubuntu_ed25519` (600),
matching `.pub`, pinned `$HOME/.ssh/t630_known_hosts`, and `port/ssh_config`.
Private keys were not displayed or copied into project files. The older sanitized
rootfs backup predates this setup; it does not include these remote-access changes.

Logs: tablet `/var/log/t630-sshd.log` and `/run/t630-screen.log`. Startup does not
depend on systemd PID 1. This remains a root-admin experimental tablet, not a
hardened multi-user deployment; possession of the dedicated key grants full root.
No router port forwarding or Internet exposure was configured.

## Disable

Using USB serial, first disable the dedicated dispatcher hook (remove its execute
bits), then terminate the dedicated SSH listener and the `t630-screen` process.
This closes network access without touching Wi-Fi or the desktop. Do not disable
services from the only remaining SSH connection unless prepared to reconnect USB.
