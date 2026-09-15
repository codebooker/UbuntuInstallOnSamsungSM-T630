# Optional remote access after first boot

The generic image must not contain SSH private keys, trusted administrator keys,
passwords, or the development tablet's host identity. Remote access is an
**opt-in after creating the person's Ubuntu account**, not an open image default.

The current recipe provides normal-owner SSH/SFTP plus a view-only feed of the
actual tablet screen. It does not install a second desktop or interactive VNC.

## On the tablet

Inside the configured Ubuntu installation, install the native dependencies:

```sh
sudo apt-get install --no-install-recommends openssh-server python3-pil
```

Copy **only** the connecting computer's ED25519 `.pub` file to a temporary
tablet path. Keep its private key on the connecting computer. From the checkout:

```sh
sudo python3 ubuntu/install-remote-access.py /path/to/computer-key.pub
```

The installer requires the selected Ubuntu owner and model/baseline marker,
checks the public-key format with OpenSSH, refuses existing dedicated remote
configuration, and generates a fresh host key locally. It installs the existing
single-instance NetworkManager helper and loopback screen service. The persistent
boot has a bounded Wi-Fi-up fallback because systemd is not PID 1 here.

The SSH policy permits only the chosen owner, only public-key authentication,
and local forwarding only to `127.0.0.1:8765`. Root, password, keyboard-interactive,
agent, X11, remote TCP, and Unix-socket forwarding are not permitted. Ordinary
administration can use `sudo` and the person's password on their own terminal;
the development USB console remains the recovery path.

## Pin trust before connecting

Obtain `/etc/ssh/ssh_host_t630_ed25519_key.pub` and its fingerprint through the
trusted USB console or the physical tablet:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_t630_ed25519_key.pub
```

Create a dedicated computer-side known-hosts entry containing `TABLET_IP`,
`ssh-ed25519`, and that public host key. Use a dedicated SSH configuration with
the chosen username, your private-key path, `IdentitiesOnly yes`,
`StrictHostKeyChecking yes`, and the dedicated `UserKnownHostsFile`. Do not
disable host checking or replace the original lab-root trust entry when the
clean installation has a different key.

Start a local-only screen tunnel using that configuration:

```sh
ssh -F /path/to/dedicated-config -N \
  -L 127.0.0.1:18765:127.0.0.1:8765 \
  -o ExitOnForwardFailure=yes tablet
```

Open `http://127.0.0.1:18765/` on the computer. It follows the physical panel's
orientation and is view-only. Closing the tunnel closes computer-side access to
the feed; the tablet feed itself is never bound to the LAN.

## Tested boundary and remaining work

The personalized clean root passes owner SSH, rejection of root/non-key login,
actual PNG delivery through the tunnel, direct-LAN refusal, and concurrent
startup without duplicate screen listeners. Its remote startup still needs a
clean cold-boot acceptance test. Earlier lab-root automatic remote startup
passed, but that does not prove the new owner's setup does.

This remains a lab port, not a hardened appliance: the retained USB root console
and parent compositor still weaken the physical login boundary. No Internet or
router port-forwarding configuration is part of this recipe. See the
[physical report](reports/clean-root-remote-pen-apps-20260915.md).
