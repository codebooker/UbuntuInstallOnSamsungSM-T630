# SM-T630 completion roadmap

## Current priority order

1. Complete automatic shallow-suspend acceptance while unplugged.
2. Remove the development account from device integration and implement the
   normal first-boot account flow.
3. Build and exercise a reproducible installer and complete stock-recovery path.
4. Camera capture, front-camera tuning, and photo-flash integration.
5. Bluetooth headset playback, microphone, and reconnect testing.
6. Four-edge and post-resume sensor/rotation validation.
7. GPU stability and browser-video isolation.
8. microSD, USB host, GPS, NFC, and external-display coverage.
9. Android application support through a coherent kernel and matching module
   payload. This is deliberately last because changing the required namespace
   options invalidates every audited stock Samsung module.

## End-user installer requirement

The release installer must not clone the development tablet's `tablet` account,
password, SSH keys, network credentials, machine identity, or runtime state. It
should install a generic Ubuntu system, then present a normal first-boot flow for
language, time zone, Wi-Fi, username, password, and optional accessibility and
privacy choices. Device integration belongs in packages or image overlays that
do not depend on a particular human username or UID. Recovery and a return-to-
stock path must be documented before the installation is called end-user ready.

The intended pages follow Ubuntu Desktop's normal order and terminology:
language, accessibility, keyboard, network, account/computer name/password,
time zone, and privacy/welcome. The result must use the person's chosen account
for GNOME, application data, authentication, audio, Waydroid, and remote access;
the current hard-coded lab account is not a shippable default. Ubuntu 24.04's
[release notes](https://documentation.ubuntu.com/release-notes/24.04/) say that
OEM installs are not supported by its desktop installer, so this image needs a
tested first-boot provisioning flow rather than a misleading OEM-mode shortcut.

## Android applications

The reference Tab S9 Ultra project uses Waydroid with an ARM64-only LineageOS
image. The SM-T630 already exposes binderfs, binder/hwbinder/vndbinder, ashmem,
overlayfs, cgroups, veth, bridge, and built-in IPv4 Netfilter/NAT support. Its
current Samsung 5.4 configuration lacks PID, IPC, and user namespaces, two cgroup
controllers, the Xtables CHECKSUM target, and the System V IPC dependency.

An isolation build proved that enabling the missing namespace and cgroup
features changes the module-version ABI. All 235 audited stock modules are
affected, so a boot-image-only Waydroid kernel is not a viable release path.
Android work is deferred until the native Ubuntu installation is complete and
the project can build and validate a coherent kernel plus matching module
payload. No Android image should be installed before that gate passes.
