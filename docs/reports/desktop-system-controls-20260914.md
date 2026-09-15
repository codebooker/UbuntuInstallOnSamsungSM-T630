# GNOME desktop system controls (2026-09-14)

## Result

The personalized clean root regressed three ordinary desktop paths: Home and
Recents had no GNOME bindings, the app grid exposed a dead `X-GNOME Utilities`
folder, and `gnome-control-center` was absent. GNOME's top-right Power Off item
also called a SessionManager method that the minimal tablet session did not
implement, while Restart was hidden because capability discovery failed.

The deterministic desktop-runtime package now:

- installs GNOME Settings as a normal Ubuntu dependency and exposes it through
  favorites, the app grid, and Tablet Controls in Quick Settings;
- asserts Home as `XF86HomePage` and Recents as `XF86Launch6` at every start;
- removes the empty distro app-folder list after Shell finishes initialization;
- implements GNOME's Logout, Restart, Power Off, CanShutdown, and IsInhibited
  SessionManager surface; and
- sends confirmed power actions through the owner-only local display socket to
  the existing exact-device, root-owned, orderly shutdown helper.

Logout deliberately locks this single-user nested session rather than exposing
the retained recovery compositor as a logged-out desktop. The outer helper
accepts only `reboot` or `poweroff`, validates the selected root and device
boundary, stops the tablet services, waits for processes, unmounts without
force or lazy detachment, and invokes the selected BusyBox system action.

## Physical checks

The package installed on the selected physical clean root with an empty dpkg
audit. After a clean GNOME-session restart, Tablet Controls version 6 was
active, the app-folder setting was empty, Home/Recents bindings were present,
and the standard Settings package was installed. Both Shutdown and Reboot
methods opened GNOME Shell's real end-session dialog and were canceled. The
SessionManager log contained only its ready line; no timeout or method error
occurred.

Boot v5 embeds the matching dual-action outer helper. It was built twice with
identical output, written only after validating the exact v4 boot hash, read
back as
`d1f475dc2e2194f0ccfc03d83d06102e72a5c1ac4a9e76ed4e622f7121010638`,
and left vendor_boot, init_boot, DTBO, and vbmeta unchanged. Cold-boot and
confirmed-power-off checks remain pending so neither action was triggered
without the person at the tablet choosing it.
