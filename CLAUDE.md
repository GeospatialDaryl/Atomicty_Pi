# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Build modern Debian (Trixie) images for the Atomic Pi SBC using Armbian's `uefi-x86` target as a base. This repo is an Armbian **userpatches profile** — not a fork. All Atomic Pi-specific work lives under `armbian/userpatches/`.

## Build Commands

```bash
# Minimal image (headless, systemd-networkd, ~3.5 GB)
./scripts/build-minimal.sh

# Server image (NetworkManager, Podman, ~6 GB)
./scripts/build-server.sh

# Dev image (kernel headers, DKMS, ~9 GB)
./scripts/build-dev.sh

# Or call Armbian directly:
cd ~/src/armbian-build
./compile.sh build \
  USERPATCHES_PATH="$HOME/Claude/Atomic_Pi/armbian/userpatches" \
  atomicpi-minimal
```

Build host: Ubuntu 22.04 or 24.04. `ARMBIAN_BUILD_DIR` defaults to `~/src/armbian-build`.

## Repository Structure

```
armbian/userpatches/
  config-atomicpi-common.conf     Shared base (BOARD, RELEASE, BRANCH, extensions)
  config-atomicpi-minimal.conf    Headless baseline, systemd-networkd, 3.5 GB
  config-atomicpi-server.conf     Server + Podman, NetworkManager, 6 GB
  config-atomicpi-dev.conf        + kernel headers, INSTALL_HEADERS=yes, 9 GB
  config-atomicpi-desktop.conf    XFCE, build after headless proven, 11 GB
  customize-image.sh              Post-build hook: overlay rsync → services → DKMS
  overlay/                        Files rsynced into image root (/tmp/overlay → /)
    etc/modprobe.d/               dw_dmac blacklist
    etc/sysctl.d/                 2 GB RAM tuning
    etc/udev/rules.d/             GPIO chip ownership
    etc/asound.conf               XMOS as ALSA default device
    etc/systemd/system/           XMOS, mic, firstboot services
    etc/atomicpi/profile          Board identity marker
    usr/local/sbin/               atomicpi-firstboot validation script
  extensions/
    atomicpi-profile.sh           Package injection via post_aggregate_packages hook
    preset-firstrun.sh            First-run wizard presets (locale, user, SSH key)
  packages/
    atomicpi-package-list.txt     Reference list of injected packages

scripts/
  build-{minimal,server,dev}.sh   Wrappers for ./compile.sh
  flash-usb.sh                    Write image to USB/SD (workstation)
  flash-emmc.sh                   Write image to eMMC (on the board)
  firstboot.sh                    Interactive post-flash hardware verification
  mount-image.sh                  Mount image for inspection (loopback)
  qemu-smoke-test.sh              Boot image in QEMU/OVMF, check for login prompt

docs/
  atomic-pi-hardware.md           Hardware reference (GPIO, audio chain, quirks)
  boot-uefi.md                    UEFI/BIOS, serial console, boot order
  emmc-install.md                 Partition layout and flash procedure
  test-matrix.md                  Hardware verification checklist
  armbian-build-notes.md          Build system docs (profiles, hooks, no-fork policy)

.github/workflows/build-armbian.yml   CI: manual dispatch, 3 profiles
BuildAttempt_1.json / .md             Build log (update after every run or decision)
```

## Hardware: Atomic Pi

- **CPU:** Intel Atom x5-Z8350 (x86-64 only — 32-bit images do not boot)
- **Boot:** AMI UEFI, GPT required. Press **Del/Tab** at splash for BIOS.
- **eMMC:** `/dev/mmcblk0`. SD card is USB-attached — appears as `/dev/sdX`, not `mmcblk1`.
- **Serial:** CN10, 115200 8N1, 3.3V TTL. Pins: 1=TX 2=RX 3=GND.

### Audio — the critical hardware path

```
GPIO 349 released → XMOS xCORE (USB Audio 2.0) → TI TAS5719 class-D → powered outputs
```

- `atomicpi-hold-xmos.service`: releases GPIO 349 at boot.
- `atomicpi-hold-mic.service`: sets GPIO 341 = 0 (mic input).
- `overlay/etc/asound.conf`: XMOS as ALSA default. Verify card name with `aplay -l`.
- `dw_dmac` blacklist is mandatory — missing it causes every shutdown/reboot to hang.

## Key Files to Edit

| Task | File |
|---|---|
| Add packages to all images | `extensions/atomicpi-profile.sh` → `PACKAGE_LIST_ADDITIONAL` |
| Add packages to one profile | `config-atomicpi-server.conf` etc. |
| Change hardware config (services, ALSA, blacklist) | `overlay/etc/...` |
| Change build variables (release, size, compression) | `config-atomicpi-common.conf` |
| Post-build runtime steps | `customize-image.sh` |
| First-run user/locale/SSH presets | `extensions/preset-firstrun.sh` |

## Build Logs

Always update `BuildAttempt_1.json` and `BuildAttempt_1.md` when a build runs, a test result is confirmed, an issue is found/resolved, or a decision changes.
