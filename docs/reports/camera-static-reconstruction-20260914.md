# Camera static-asset reconstruction (2026-09-14)

## Result

`tools/prepare_camera_static_assets.py` reconstructs the non-redistributable
static camera runtime locally from exact DZE3 `system` and `vendor` mounts. It
does not download, bundle, or publish Samsung/Qualcomm content.

The preparer verifies source SHA256 values, extracts four `apex_payload.img`
members with independently pinned output hashes, and applies two narrow binary
transformations only after validating their complete source files:

- CameraService: seven changed bytes;
- `com.qti.chi.override.so`: five changed bytes.

Every changed offset, original byte, replacement byte, complete input hash, and
complete output hash is encoded in the tool. A wrong baseline or unexpected
preimage fails before the output directory is installed. Existing or symlinked
destinations are refused, and preparation uses an atomic temporary directory.

## Physical acceptance

The tool ran against the checksum-verified read-only physical `system` and
`vendor` mappings. It produced six files totaling 172 MB under a private tablet
rehearsal directory. The runtime, i18n, VNDK 30, and Samsung camera APEX
payloads plus both patched binaries were each byte-for-byte identical to the
files used by the working camera stack.

No proprietary payload was copied to the Mac or repository. The remaining
camera installer boundary is the writable `/data/vendor/camera` seed: classify
its stock-derived calibration inputs separately from files the HAL can safely
generate on first use, then move that state to an account-neutral root-owned
location.
