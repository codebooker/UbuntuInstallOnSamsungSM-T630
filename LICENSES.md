# Licensing notes

- Original userspace scripts, documentation, and helper programs in this
  repository are offered under the repository's AGPL-3.0 license.
- Files under `patches/` are modifications to Linux/Samsung downstream kernel
  code and remain subject to GPL-2.0-only and any file-specific upstream notices.
- `patches/polkit-gnome-t630-process-agent.patch` modifies Ubuntu's
  `policykit-1-gnome` source and remains subject to its LGPL-2.0-or-later terms.
- `ubuntu/gdm-auth-only-greeter.patch` modifies Ubuntu's GDM source and remains
  subject to GDM's GPL-2.0-or-later terms. The login-runtime package also builds
  elogind under its GPL-2.0-or-later and LGPL-2.1-or-later components.
- `tools/fetch_sources.sh` downloads third-party projects into ignored working
  directories. Those projects are not relicensed and retain their own licenses.
- Samsung firmware, factory images, calibration, and proprietary Android
  libraries are not distributed by this repository.
- `ubuntu/MaliitKeyboard.qml` retains its upstream BSD-style license notice.
- `ubuntu/maliit-waylandplatform.cpp` retains its upstream LGPL-2.1 notice.
- Mutter source fragments and generated diffs in
  `tools/prepare_mutter_pen_trace.py` and
  `tools/prepare_mutter_pen_source_trial.py` retain the licenses of the files
  they modify: the X11 seat is LGPL-2.0-or-later (Red Hat, 2019; Carlos
  Garnacho), the Wayland tablet files are GPL-2.0-or-later (Red Hat, 2015;
  Carlos Garnacho), the context file is GPL-2.0-or-later (Havoc Pennington,
  Elijah Newren, Red Hat), and the syncobj file is GPL-2.0-or-later (NVIDIA,
  2023; Austin Shafer). These fragments do not relicense the downloaded source.

When contributing code copied or adapted from another project, preserve its
copyright and license notices and document the source in `docs/PROVENANCE.md`.
