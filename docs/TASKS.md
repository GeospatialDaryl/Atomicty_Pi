# Project Context

## Summary

This project builds modern Debian-based images for the Atomic Pi board.

The goal is a clean, modern, reproducible build system for x86_64 SBCs, starting with the Atomic Pi. Armbian's SBC workflow is the model — use it as an upstream dependency rather than reimplementing image creation from scratch.

## Current direction

```
Armbian uefi-x86 backend
+
Atomic Pi userpatches/profile layer
+
future pure-Debian backend using live-build or mmdebstrap (optional, later)
```

The Armbian path is the active focus. The pure-Debian backend is a future option if Armbian proves insufficient, but is not being built now.

## Guiding principles

- **No Armbian fork.** All Atomic Pi work lives in this repo under `armbian/userpatches/`.
- **No custom board file** unless hardware-specific boot behavior is discovered that cannot be handled in userpatches.
- **No kernel patches** unless a specific driver gap is found. All required drivers are mainline.
- **Profiles over monoliths.** Separate named configs (minimal, server, dev, desktop) rather than one build with flags.
- **Overlay over heredocs.** Static config files live in `armbian/userpatches/overlay/` and are rsynced into the image — not embedded as heredocs in shell scripts.
- **Extensions for packages.** Package injection uses Armbian's `post_aggregate_packages` hook for correct dependency resolution at build time.

## Build profiles

| Profile | Use case | Size |
|---|---|---|
| atomicpi-minimal | Boot/SSH/eMMC validation | 3.5 GB |
| atomicpi-server | Daily-use headless server | 6 GB |
| atomicpi-dev | Kernel/DKMS/GPIO development | 9 GB |
| atomicpi-desktop | XFCE desktop (after headless proven) | 11 GB |

## v0.1 milestone

First functional build. Criteria in `BuildAttempt_1.md`. Short form:

- Boots from USB and eMMC
- Ethernet and WiFi work
- XMOS audio service starts, powered speaker outputs work
- Clean shutdown and reboot (dw_dmac blacklist effective)
- SHA + xz compressed image output
- Documented eMMC install path
- Hardware validation checklist complete
