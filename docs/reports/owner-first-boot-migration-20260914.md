# Owner-neutral runtime and first-boot setup (2026-09-14)

The development installation previously assumed account `tablet`, UID/GID
1000, and `/home/tablet` across desktop, audio, camera, rotation, lock, and
display services. That could not support a normal installer-created account.

## Implemented

- `/etc/t630/owner` contains exactly one validated username and no shell syntax,
  path, numeric identity, password, key, or network value.
- `t630_account.py` resolves UID, GID, home and shell from the local password
  database and rejects privileged, missing, non-interactive, or unusual-home
  accounts.
- Desktop startup, app launching, login registration, audio/microphone, camera,
  rotation, lock, display control, policy and clean restart paths use the
  resolved account. Narrow privileged actions use the `t630-owner` group.
- The first-boot backend validates language, keyboard, account name, full name,
  hostname, timezone, accessibility and privacy choices. The password is
  supplied separately and only reaches `chpasswd` over stdin. The owner marker
  is written last.
- The touch-first UI provides Language, Accessibility, Keyboard, Network,
  Account, Time Zone, Privacy, and Finish pages. A preconfigured development
  tablet exits before GTK/display initialization, proving the wizard remains
  dormant when setup is complete.
- `audit_release_root.py` refuses a candidate image containing human accounts,
  home contents, network profiles, Netplan state, SSH host keys, machine IDs,
  random seeds, or completed owner/setup state. It reports categories without
  printing account or credential contents.

## Physical migration result

The existing development account was enrolled as the owner without changing
its password, home, files, UID, Wi-Fi profile, or SSH policy. A controlled clean
restart produced boot ID `a9abc5c2-744a-4291-8bf1-b1c42f3f58a7`.

Post-boot checks passed:

- GNOME ran as the resolved owner;
- the rotation FIFO was `root:t630-owner` mode 0620;
- Wi-Fi reconnected;
- Bluetooth exposed its audio source and sink profiles;
- the default speaker and microphone were `t630_speakers` and
  `t630_microphone`;
- sensors, charging, device permissions, lock/power monitor and remote access
  were healthy;
- a camera enable/ready/disable cycle succeeded through the owner-group sudo
  rule and left no camera-ready marker;
- runtime health reported zero kernel fault markers.

The sample non-secret profile in `docs/examples/first-boot-profile.json`
validated on the physical tablet. The release privacy gate correctly refused
the development root for identity/network/account categories. No account or
password was created during that validation.

## Remaining installer gate

The UI and account-neutral device layer exist, but the project still needs a
generic Ubuntu root builder, device-integration packaging, and a complete
wipe/install/first-boot/stock-recovery rehearsal before publishing an image.
