# AGENTS.md

## Project

This repository is for building modern Debian-based images for the Atomic Pi x86_64 SBC.

The near-term goal is to create reproducible Debian/Armbian-based images for the Atomic Pi using modern practices, with Armbian's `uefi-x86` target as the first backend.

## Hardware target

Primary board: Atomic Pi.

Known hardware assumptions:
- x86_64 Intel Atom-based SBC
- UEFI boot
- eMMC storage
- microSD/USB boot options
- limited RAM and storage
- intended use as a small Debian server/appliance board

## Preferred approach

Prefer a clean profile/overlay approach over forking Armbian.

Use Armbian as an upstream dependency and keep Atomic Pi-specific configuration in this repository, under:

```
armbian/userpatches/
  config-atomicpi-common.conf
  config-atomicpi-minimal.conf
  config-atomicpi-server.conf
  config-atomicpi-dev.conf
  config-atomicpi-desktop.conf
  customize-image.sh
  overlay/
  extensions/
  packages/
```

Do not create a new Armbian board file or fork the Armbian build framework. The existing `uefi-x86` board config is sufficient.

## Build system

Armbian is cloned separately (default: `~/src/armbian-build`). The connection is via `USERPATCHES_PATH`:

```bash
./compile.sh build \
  USERPATCHES_PATH="$HOME/Claude/Atomic_Pi/armbian/userpatches" \
  atomicpi-minimal
```

Wrapper scripts: `scripts/build-minimal.sh`, `scripts/build-server.sh`, `scripts/build-dev.sh`.

## Key files for AI agents

| File | Purpose |
|---|---|
| `CLAUDE.md` | Primary guidance for Claude Code — read this first |
| `BuildAttempt_1.json` | Machine-readable build/test log — update after every run |
| `BuildAttempt_1.md` | Human-readable companion log |
| `docs/armbian-build-notes.md` | How the Armbian build system is used |
| `docs/atomic-pi-hardware.md` | Hardware reference (GPIO, audio chain, quirks) |
| `docs/test-matrix.md` | Hardware verification checklist |
