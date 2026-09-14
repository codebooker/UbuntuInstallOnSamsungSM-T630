#!/bin/sh
# Historical writer retained so the unsafe v9 artifact fails closed.
set -eu

cat >&2 <<'EOF'
REFUSED: waydroid-kernel-v9 changes the SM-T630 kernel module ABI.

Physical testing proved that the stock Samsung hardware modules cannot load
against this kernel. Every audited stock module is affected, including Wi-Fi,
display, camera, audio and touch dependencies. The v9 image must not be written
to BOOT, even for a temporary test.

Android support is deferred until the project can build and validate one
coherent kernel plus matching vendor module payload. See:
docs/reports/waydroid-prerequisites-20260913.md
EOF
exit 1
