# Personalized clean-root remote access and pen apps — 2026-09-15

Selected root: `/run/ubuntu/opt/t630/rehearsal/release-root`. Tests retained boot
ID `2dc5b3c3-b305-474e-a7c2-64efc87899f9`; no tablet reboot was needed.

## Pen apps

Native Xournal++ 1.2.2 and MyPaint 2.0.1 installed and launched inside the
normal-owner nested GNOME session. A scanout visibly contains continuous physical
Xournal++ handwriting; MyPaint opens maximized with dark controls. Input
pressure is not accepted: host Xwayland advertises it, inner GTK initially saw
only X/Y and missed the stylus device. Explicit tool-type/serial metadata and a
guarded idle-pen refresh make the stylus visible, pending physical pressure tests.
The experiment is nonpersistent and not automatically installed.

Krita 5.2.2 forced X11, then explicitly rejected native Wayland when an
app-specific environment experiment reached its application startup. The shim
and broken override were removed; no bypass is shipped. See [pen apps](../PEN-APPS.md).

Missing `at-spi2-core` caused accessibility-bus activation warnings. It is now
installed and explicit in both public everyday-app dependency recipes; fresh
GTK inventory no longer reports that missing service. MyPaint's recommended
brush/background extras are explicit in its optional recipe.

## Clean-root remote access

`ubuntu/install-remote-access.py` is an opt-in on-device recipe, requiring one
ordinary ED25519 **public** key and an already personalized owner. It refuses
existing dedicated destinations rather than silently replacing another remote
policy, and creates a fresh dedicated host key only on the tablet. The installer
does not distribute keys, passwords, or owner identity.

Installed native OpenSSH and Pillow. The source-built scanout helper was already
present in the native-userspace package. The current source `stop-ubuntu` matched
the accepted outer helper, so startup did not downgrade the boot's shutdown path.

Verified on the same boot:

- SSH authenticates as the selected normal Ubuntu owner, UID 1000, not root.
- Login with public-key authentication disabled is rejected.
- Root login with the otherwise valid key is rejected.
- Screen HTML and PNG return HTTP 200 through the SSH tunnel.
- The screen feed listens on tablet loopback; direct LAN access is refused.
- The Mac tunnel binds to local loopback only.
- Two concurrent startup calls leave one SSH listener and one screen process,
  with no screen-service error log.
- Host public key obtained through USB before SSH and pinned in a separate
  clean-install known-hosts file, preserving the original lab-root trust file.

New clean-install host fingerprint:
`SHA256:ZWZp6YJi796yBk/eEtu0G6x1N1KfdDj7KQJ0k+Uk26M`.

The optional helper is compatible with the boot image's bounded Wi-Fi-up remote
fallback. **No clean-root remote cold-boot test has been performed yet**, since
the handwriting test document remains open. Full shutdown filesystem-busy
acceptance is also still pending.

Follow-up: the [subsequent orderly restart report](clean-root-restart-folders-20260915.md)
records automatic clean-root remote startup, saved-note preservation, and the
qualification that idle GTK axes alone cannot establish pressure loss. The
same-boot observations above describe the earlier stage, not current acceptance.

All app downloads were written to the tablet, not the Mac. The tablet retained
more than 85 GiB free; the Mac data volume showed 60 GiB available. Only small
diagnostic screenshots and source files were created locally.
