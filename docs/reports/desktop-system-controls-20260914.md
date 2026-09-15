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

A subsequent tablet restart exposed that the owner-session launcher still
reapplied its early flat-purple development background on every start. Those
two background writes are now absent from the persistent owner launcher, while
the disposable pre-account installer retains its deliberate dark fallback.
GNOME's per-user wallpaper URI and presentation mode therefore remain owned by
the user's dconf profile across restarts.

Boot v5 first embedded the dual-action outer helper. Boot v6 then added safe
clean-root reselection after an orderly action. V6 was built twice with
identical output, written only after validating the exact v5 boot hash, read
back as
`ca7caa12d1228969b264815bf69f34dbbee5ced9e3a86d1134c590bff8c895dc`,
and left vendor_boot, init_boot, DTBO, and vbmeta unchanged. Its next restart
selected the clean root, started managed GNOME, and retained the saved wallpaper
settings. Confirmed full Power Off remains pending so the tablet was not left
off without the person at the tablet choosing it.
