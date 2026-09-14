# PolicyKit authentication runtime package (2026-09-14)

## Result

`tools/build_t630_polkit_runtime.sh` now builds the app-store authentication
adapter from Ubuntu's exact `policykit-1-gnome` 0.105-7ubuntu5 source package:

- name: `t630-polkit-runtime_0.1.0_arm64.deb`
- size: 25,578 bytes
- SHA256: `baa7fbcd300895bd6754eac6dec95061f9f99a8a56c8f5a4d5ac059193f886da`
- upstream archive SHA256:
  `1784494963b8bf9a00eedc6cd3a2868fb123b8a5e516e66c5eda48df17ab9369`
- Ubuntu patch archive SHA256:
  `957ebefe04c896fc621ef8c578f6e77f04e72cd2092c6500b47e578ae91d1cf1`

Two native ARM64 builds were byte-identical. The builder verifies both source
archives, applies Ubuntu's ordered patch series, then applies the tracked T630
process-subject and Wayland-focus patch. It writes an uninstalled Debian package
and never replaces the live agent.

## Security boundary

The adaptation changes how the authentication agent identifies its session; it
does not grant authorization. Ubuntu's PolicyKit rules and PAM stack still make
the decision and verify the password. The agent refuses root, system accounts,
UIDs outside the normal human range, malformed process IDs, and processes not
owned by the calling account. It no longer assumes the development tablet's UID
1000, so it follows the account created by first boot.

PolicyKit's D-Bus activation file is reversibly diverted so `polkitd` starts as
its own user with `no_new_privs` on this non-systemd host. This works around the
stock kernel's post-privilege-drop `/proc/self/fdinfo` restriction without
relaxing PolicyKit policy.

## Clean-root acceptance

The package installed in the identity-clean rehearsal root with no unresolved
libraries. A root invocation was rejected. With `/proc` temporarily bind-mounted,
a UID 1000 agent accepted a UID 1000 target and proceeded through validation to
the expected headless GTK failure, proving the hard-coded UID was gone. The
temporary mount was removed. Package removal restored the original Ubuntu D-Bus
service at SHA256
`baed12288339ed4b1df90f017beb8af07b56eba1b2edc4a60914880c13617af1`
and removed the diversion. Final reinstall, the twelve-file release apply,
identity audit, library checks, package audit, and mount-leak check all passed.

End-to-end password approval was already physically proven on the live tablet
with the earlier binary. The new owner-neutral build still needs the same
on-screen store transaction after the clean-root boot rehearsal.
