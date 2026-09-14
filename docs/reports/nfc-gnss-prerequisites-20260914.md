# NFC and GNSS prerequisite audit (2026-09-14)

This report narrows the remaining NFC and location work without loading a new
driver or starting a proprietary service. It combines the exact DZE3 kernel
source with a read-only inventory from the physical SM-T630. Android
application/container support is a separate, deliberately deferred project.

## NFC hardware path

The active device tree exposes the tablet controller at I2C bus 22, address
`0x2b`:

- compatible string: `pn547`
- IRQ, enable, firmware-download, and clock-request GPIOs
- Qualcomm AP selection
- clock-request wake support
- regulator-backed `nfc_pvdd`

The `pn547` name is the compatibility ABI. This kernel was actually compiled
with Samsung's SN100 feature path (`CONFIG_NFC_FEATURE_SN100U=y`) and packages
the driver as `nfc_sec.ko`. The module's version magic matches the running
DZE3-compatible kernel. On the physical tablet the I2C device exists, but it is
unbound; the module was not loaded and no `/dev/pn547` node existed.

The matching stock vendor image contains NXP's NFC 1.2 HIDL service, the NXP
NCI implementation, Samsung's NFC 2.0 interface library, product configuration,
permissions, and init rules. The service is an Android HIDL executable rather
than a native Linux NFC daemon. It therefore cannot be made into a GNOME NFC
device by copying a binary or enabling a systemd unit alone.

## NFC safety gate

Loading the module is not a read-only test. Its probe requests the GPIOs and
interrupts, enables `nfc_pvdd`, resets the controller, and immediately sends an
I2C command. The stock module's remove path does not mirror every acquired
resource: notably it does not explicitly power the regulator off or release the
clock-request interrupt. The shutdown path does power the regulator down, but
that path is not the normal module-unload path.

For that reason this repository does not auto-load `nfc_sec.ko`. Before a
physical tag test, the project needs all of the following:

1. a corrected and tested teardown path for the exact source/module;
2. a bounded lifecycle helper that fails NFC off;
3. an isolated Android HIDL environment for the stock NXP/Samsung libraries;
4. a small bridge from that environment to a supported Ubuntu-facing API;
5. suspend, resume, repeated enable/disable, and passive-tag tests.

Force-loading a mismatched module, poking the I2C device directly, or leaving
the regulator powered after a failed service start is outside the safe path.

## GNSS/GPS path

The kernel provides the generic GNSS framework, but the running system exposes
no GNSS class device or native location provider. The stock vendor image shows
the real implementation boundary:

- `android.hardware.gnss@2.1-service-qti`
- Qualcomm `loc_launcher`, `xtra-daemon`, and location libraries
- Samsung GNSS 2.0 plus Qualcomm GNSS HIDL interfaces
- `gps.conf`, `izat.conf`, antenna configuration, certificates, and seccomp
  policy

The service depends on Android HIDL plus Qualcomm vendor frameworks and modem
transport. It is therefore another isolated proprietary-service integration,
not a missing `gpsd` package. Starting the binary outside its expected Binder,
property, permissions, firmware, and QMI environment would not be a meaningful
test.

The safe implementation sequence is to identify the exact transport and
firmware nodes, extend the already bounded vendor-runtime mount model without
starting unrelated Android services, then bridge fixes to GeoClue. Acceptance
requires a cold outdoor fix, GNOME location permission behavior, suspend/resume,
and confirmation that no Android calibration partition is modified.

## Result

NFC and GNSS are now classified rather than unknown. The hardware descriptions,
matching kernel support, and proprietary payloads are present. Neither feature
is release-ready, but neither requires the Waydroid namespace kernel. They can
be developed later as narrow hardware-service bridges while Android application
support remains the final roadmap item.
