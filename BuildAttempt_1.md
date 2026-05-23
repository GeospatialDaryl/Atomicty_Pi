# Atomic Pi Debian Build — Attempt 1

**Started:** 2026-05-22  
**Host:** pending first run  
**Target:** Intel Atom x5-Z8350 · Debian Trixie (amd64)  
**Goal:** Bootable modern Debian image for Atomic Pi with full hardware support, especially XMOS-driven powered speaker outputs.

---

## Status: Scaffolded — Armbian approach — Not Yet Run

All scripts and configuration files have been written. No build has been executed yet.

---

## Strategy Pivot (2026-05-22)

**From:** Custom debootstrap pipeline (5-stage shell scripts, manual GPT/EFI image assembly)  
**To:** Armbian `uefi-x86` base + Atomic Pi userpatches overlay

**Why:**  
Armbian already maintains a `uefi-x86` target at Standard support tier with Debian Trixie. It provides everything we were going to build manually — GPT/EFI image layout, GRUB bootloader, kernel/initramfs integration, SBC-style build automation, and GitHub Actions support. Building on top of it means we write an overlay (a `customize-image.sh` hook), not a distro.

The original debootstrap scripts (stages 01–05) have been removed. The hardware config files from `files/` have been absorbed into `customize-image.sh` as heredocs so the hook is self-contained.

---

## Architecture

```
armbian/build (cloned)
  └─ compile.sh BOARD=uefi-x86 RELEASE=trixie
       ├─ builds standard Armbian Trixie image
       └─ calls userpatches/customize-image.sh
            ├─ [1] dw_dmac blacklist        (prevents shutdown hang)
            ├─ [2] sysctl tweaks            (2 GB RAM tuning)
            ├─ [3] udev GPIO rules          (audio group owns gpiochip*)
            ├─ [4] XMOS systemd services    (GPIO 349 → powered audio)
            ├─ [5] ALSA config              (XMOS as default device)
            ├─ [6] non-free firmware        (Realtek, MediaTek, BT)
            └─ [7] DKMS GPIO modules        (i2c/spi-gpio-custom)
```

---

## Audio Chain (Critical Path)

```
Boot
 └─ atomicpi-hold-xmos.service
      └─ GPIO 349: assert reset (0) → wait 0.1s → release (1)
           └─ XMOS xCORE enumerates as USB Audio 2.0
                └─ TI TAS5719 class-D amp receives I2S
                     └─ Powered speaker outputs
                          1.5 W/ch @ 5 V
                          5.0 W/ch @ 12 V
atomicpi-hold-mic.service (after XMOS)
 └─ GPIO 341 = 0  → microphone input selected
```

ALSA: `asound.conf` sets `hw:XMOS,0` as the `pcm.!default` device.  
PulseAudio: `default-sink.pa` tries to prefer the XMOS USB sink.

---

## File Inventory

```
build_atomicpi.sh                     Wrapper: clones Armbian + runs compile.sh
armbian/config-atomicpi-minimal.conf  Armbian build vars (minimal image)
armbian/config-atomicpi-server.conf   Armbian build vars (server image, more packages)
armbian/userpatches/customize-image.sh  Atomic Pi hardware layer hook (7 steps)
armbian/userpatches/packages/         Drop .deb files here for auto-install
scripts/flash-usb.sh                  Write image to USB/SD (workstation)
scripts/flash-emmc.sh                 Write image to eMMC (on the board)
scripts/firstboot.sh                  Post-boot verification script
.github/workflows/build-armbian.yml   GitHub Actions CI workflow
docs/hardware.md                      Hardware reference
docs/boot-notes.md                    UEFI, serial console, boot order notes
docs/image-layout.md                  Partition layout and flash procedure
docs/test-matrix.md                   Hardware verification checklist
```

---

## Build Command

```bash
# Full minimal image build
./build_atomicpi.sh minimal

# Server image (more packages)
./build_atomicpi.sh server

# Update Armbian build framework
./build_atomicpi.sh --update-armbian
```

Armbian build requires Ubuntu Jammy (22.04) or Noble (24.04) as the host OS.

---

## Open Questions / Known Risks

1. **XMOS card name in ALSA** — `asound.conf` references card name `"XMOS"`. Must verify with `aplay -l` on first live boot. If the XMOS enumerates under a different name, update `asound.conf` and note here.

2. **PulseAudio XMOS sink name** — `default-sink.pa` uses a guessed sink name (`XMOS xCORE USB Audio 2.0`). Verify with `pactl list sinks short` on first live boot.

3. **sysfs GPIO in newer kernels** — The `/sys/class/gpio/` interface is deprecated since kernel ~5.3 but still present in 6.x. If Armbian's `current` branch kernel removes it, the systemd services need to switch to `gpioset` (from `gpiod` package) or Python `gpiod` library.

4. **Armbian linux-headers package name** — `PACKAGE_LIST_ADDITIONAL` in the server config uses `linux-headers-current-x86`. Verify this is the correct Armbian package name after first build (check `apt-cache search linux-headers` in a running image).

5. **DKMS in-build cloning** — `customize-image.sh` clones from GitHub during the build. Armbian normally has network in chroot; if not, pre-clone the repos into `armbian/userpatches/packages/` and update the paths.

6. **Network-boot priority after CMOS reset** — BIOS may default to PXE before eMMC. Document in boot-notes.md once confirmed.

---

## Stage Run Log

*(Updated when build is executed)*

### Stage 1: Armbian base build

*Not yet run.*

### Stage 2: customize-image.sh

*Not yet run.*

### Stage 3: Flash and test

*Not yet run.*

---

## Test Results

*(Populated after first flash — see docs/test-matrix.md)*

---

## Issues Found

*(None yet)*
