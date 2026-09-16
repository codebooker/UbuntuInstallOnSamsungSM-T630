# Waydroid GAPPS acceptance (2026-09-16)

## Result

The physical SM-T630 now boots the official Waydroid ARM64 GAPPS LineageOS 20 /
Android 13 system with the matching official MAINLINE vendor image. Google Play
services, Google Services Framework, and Play Store are present. The Play Store
reaches its unauthenticated sign-in activity, Android resolves DNS, and an
HTTPS request from Android's network namespace receives the expected `204`
response from Google's connectivity endpoint.

The migration started from the previously accepted VANILLA runtime. Exact
images, Waydroid configuration, overlays, LXC configuration, host permissions,
and the owner's private Android data were backed up under a root-only directory
before `waydroid init -s GAPPS -f`. The owner data remained in place: F-Droid
1.23.2 was still installed after migration and after a subsequent clean Android
stop/start cycle. The rollback backup remains private and is intentionally not
part of this repository.

## Accepted image boundary

- System ZIP: `lineage-20.0-20260403-GAPPS-waydroid_arm64-system.zip`
- ZIP size: 1,326,285,880 bytes
- ZIP SHA-256: `c5e557605887664ab1da6c17ff0032317735a0425b8055ee9073fdbcd00899c2`
- Extracted `system.img` SHA-256:
  `b21bb8508157fdd3fe0611d5770c9103403a4a0834f3713650ddcf25a6fb1578`
- MAINLINE `vendor.img` SHA-256:
  `b18a05747db565c134db48031caeec3ce4bd9e0ce8f88ef9c679f3ef9e24e39a`
- System OTA channel:
  `https://ota.waydro.id/system/lineage/waydroid_arm64/GAPPS.json`
- Vendor OTA channel:
  `https://ota.waydro.id/vendor/waydroid_arm64/MAINLINE.json`

The repository does not redistribute either image.

The read-only acceptance checker is packaged in
`t630-waydroid-runtime_0.1.5_all.deb`. The reproducible package SHA-256 is
`be26ed7cad0e96d2d4e1281099ccedc2a7ff764c94ca63356b1ba4a772f0b693`.
That package was installed on the physical tablet and its packaged checker
passed after installation.

## Physical checks

The first GAPPS boot and a clean restart both reached
`sys.boot_completed=1`. After the clean restart:

- `com.android.vending`, `com.google.android.gms`, and
  `com.google.android.gsf` were installed;
- Google Play services and the Google apps process were running;
- Google check-in completed successfully and populated a registration ID;
- the registration ID was checked only for existence and was not printed,
  recorded, or committed;
- Play Store cold-launched
  `com.google.android.finsky.unauthenticated.activity.UnauthenticatedMainActivity`;
- DNS resolved `connectivitycheck.gstatic.com` and HTTPS returned status 204;
- `system_server` retained the same PID during the stability interval;
- its trace descriptor resolved to canonical
  `/sys/kernel/tracing/trace_marker`; and
- the clean-restart crash buffer contained no new fatal entry.

The initial migration boot produced one graphics-composer abort while Android
was optimizing the new system. The service recovered, remained stable, and the
abort did not recur on the clean restart. No workaround was installed for a
non-reproducible first-boot event.

## Account and certification boundary

No Google credentials were entered, captured, or stored by the project. The
owner must perform Play Store sign-in on the tablet. If Google reports the
Waydroid identity as uncertified, the owner can follow Waydroid's official
[Google Play certification guide](https://docs.waydro.id/faq/google-play-certification)
to submit the local Google Services Framework ID at Google's registration page.
That identifier and all account material are private state and must stay out of
support logs and repository artifacts.

Device registration is not equivalent to high-level Play Integrity or hardware
attestation. Applications that require those facilities, protected DRM, or a
stock-certified device may remain incompatible.
