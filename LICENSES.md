# Licensing notes

- Original userspace scripts, documentation, and helper programs in this
  repository are offered under the repository's AGPL-3.0 license.
- Files under `patches/` are modifications to Linux/Samsung downstream kernel
  code and remain subject to GPL-2.0-only and any file-specific upstream notices.
- `patches/polkit-gnome-t630-process-agent.patch` modifies Ubuntu's
  `policykit-1-gnome` source and remains subject to its LGPL-2.0-or-later terms.
- `tools/fetch_sources.sh` downloads third-party projects into ignored working
  directories. Those projects are not relicensed and retain their own licenses.
- Samsung firmware, factory images, calibration, and proprietary Android
  libraries are not distributed by this repository.
- `ubuntu/MaliitKeyboard.qml` retains its upstream BSD-style license notice.
- `ubuntu/maliit-waylandplatform.cpp` retains its upstream LGPL-2.1 notice.

When contributing code copied or adapted from another project, preserve its
copyright and license notices and document the source in `docs/PROVENANCE.md`.
