# Rear flashlight bring-up (2026-09-13)

The stock device tree maps the rear camera-flash controller to the PM8350C LED
nodes `led:torch_0` and `led:switch_0`. Writing torch current alone changes the
kernel value but produces no visible light. The tested sequence is current
first, followed by switch value `1`; shutdown clears current and then the
switch. A physical three-second test at 100/500 was confirmed visible.

The GNOME Quick Settings integration deliberately caps continuous operation at
300/500, validates the exact node names, common controller, and advertised
limits, and renews a 15-second lease every five seconds. Loss of GNOME Shell or
the extension therefore lets the light fail off. Power-monitor startup and
orderly shutdown also force both nodes off.

The first desktop-only restart exposed two previously latent lifecycle issues:
camera and video setup had independently published byte-identical Adreno files,
and elogind changed its recreated session IDs from `cNN` to `NN`. Startup now
accepts only the known identical firmware source and both of elogind's numeric
ID forms. The managed desktop also has its own process group so stopping its
wrapper cannot orphan GNOME or Xwayland.
