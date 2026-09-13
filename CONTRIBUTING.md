# Contributing

This is hardware enablement work, so reproducible evidence matters more than a
bare “works for me.” For device reports, include:

- exact model and region/carrier variant;
- `ro.product.device`, build number, bootloader version, and kernel string;
- cold boot versus warm restart;
- the exact commit and changed files;
- what was physically observed and what was inferred from logs.

Do not upload Samsung firmware, calibration data, device serial numbers, MAC
addresses, Wi-Fi profiles, passwords, private keys, or personal screenshots.

Keep destructive operations model- and partition-specific, fail closed on
unexpected values, and provide an explicit recovery path. Do not weaken an
existing identity, size, hash, charge-state, or mount-state guard simply to make
a new device pass.
