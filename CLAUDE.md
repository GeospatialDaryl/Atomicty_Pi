# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Build a modern Debian (Trixie) image for the Atomic Pi SBC by treating it as an overlay profile on top of Armbian's maintained `uefi-x86` target — not a new board port. The Atomic Pi-specific layer lives entirely in `armbian/userpatches/customize-image.sh`.

## Build Commands

```bash
# Full build (minimal image, Debian Trixie)
./build_atomicpi.sh minimal

# Server image (more packages)
./build_atomicpi.sh server

# Update Armbian build framework clone
./build_atomicpi.sh --update-armbian
```

Build host must be Ubuntu Jammy (22.04) or Noble (24.04). Run as a normal user — Armbian's `compile.sh` will sudo what it needs.

## Repository Structure

```
build_atomicpi.sh                     Wrapper: clones Armbian, runs compile.sh
armbian/
  config-atomicpi-minimal.conf        BOARD=uefi-x86 RELEASE=trixie BUILD_MINIMAL=yes
  config-atomicpi-server.conf         Same + PACKAGE_LIST_ADDITIONAL for dev tools
  userpatches/
    customize-image.sh                THE key file — Atomic Pi hardware layer
    packages/                         Drop .deb files here for Armbian auto-install
scripts/
  flash-usb.sh                        Write image to USB (on workstation)
  flash-emmc.sh                       Write image to eMMC (on the board, from USB boot)
  firstboot.sh                        Post-flash verification (audio, GPIO, network)
docs/
  hardware.md                         Full hardware reference (GPIO, audio chain, quirks)
  boot-notes.md                       UEFI/BIOS, serial console, boot order
  image-layout.md                     GPT partition layout and flash procedure
  test-matrix.md                      Verification checklist for each hardware feature
.github/workflows/build-armbian.yml   CI build on push to main
BuildAttempt_1.json                   Machine-readable build log (updated each session)
BuildAttempt_1.md                     Human-readable build log (updated each session)
```

## Hardware: Atomic Pi

- **CPU:** Intel Atom x5-Z8350 (Cherry Trail, x86-64 only)
- **Boot:** AMI UEFI, GPT required. Press **Del/Tab** at splash for BIOS.
- **eMMC:** `/dev/mmcblk0`. SD card appears as USB mass storage, not `mmcblk1`.
- **Serial console:** CN10, 115200 8N1, 3.3V TTL, pins 1=TX 2=RX 3=GND.

### Audio — the critical hardware path

```
GPIO 349 released → XMOS xCORE (USB Audio 2.0) → TI TAS5719 class-D → powered speaker outputs
```

- `atomicpi-hold-xmos.service`: toggles GPIO 349 at boot to bring XMOS out of reset.
- `atomicpi-hold-mic.service`: sets GPIO 341 = 0 (microphone input, not loopback).
- `asound.conf`: sets `hw:XMOS,0` as ALSA default device.
- HDMI is card 0; XMOS is card 1. Verify card name with `aplay -l` on first boot.

### Mandatory kernel module blacklist

`dw_dmac` and `dw_dmac_core` must be blacklisted or the board hangs on every shutdown/reboot. Installed by `customize-image.sh` step 1.

### Out-of-tree DKMS modules

`i2c-gpio-custom` and `spi-gpio-custom` (from github.com/digitalloggers) are required for the GPIO-bitbanged I2C/SPI buses (BNO055 IMU, onboard RTC). Built and installed by `customize-image.sh` step 7.

## Key Files to Edit for Common Tasks

| Task | File |
|---|---|
| Add/remove packages from image | `armbian/config-atomicpi-server.conf` → `PACKAGE_LIST_ADDITIONAL` |
| Change hardware config (services, ALSA, GPIO) | `armbian/userpatches/customize-image.sh` |
| Change Debian release or kernel branch | `armbian/config-atomicpi-minimal.conf` |
| Update flash procedure | `scripts/flash-emmc.sh` |
| Add test cases | `docs/test-matrix.md` |

## Build Logs

Always update `BuildAttempt_1.json` and `BuildAttempt_1.md` when:
- A build is run (record outcome, timestamps, any errors)
- A hardware test result is confirmed
- A new issue is found or resolved
- A decision is changed from what was previously recorded

The JSON is the source of truth for automated parsing; the MD is the human-readable companion.
