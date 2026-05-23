# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Build a modern Debian (Bookworm or later) flashable image for the Atomic Pi SBC, replacing the outdated manufacturer-provided Lubuntu image. The image must preserve full hardware functionality, especially the onboard XMOS-driven powered speaker outputs.

## Hardware Reference

**SoC**: Intel Atom x5-Z8350 (Cherry Trail, x86-64 only — 32-bit images will not boot)
**RAM**: 2GB
**Storage**: 16GB eMMC at `/dev/mmcblk0`
**Boot**: AMI UEFI BIOS (press Del or Tab at splash). Serial console on CN10: 115200 baud, 3.3V TTL, pins 1=TX 2=RX 3=GND.

**Networking**
- Ethernet: Realtek RTL8111G (mainline kernel, works out of the box)
- WiFi: MediaTek RT5572 (USB bus, driver: `rt2800usb`)
- Bluetooth: Qualcomm CSR8510 (USB bus)

**Audio — the critical subsystem**
The XMOS xCORE digital audio processor sits on the USB peripheral bus and feeds a TI TAS5719 class-D stereo amplifier (~1.5W/ch at 5V, up to 2×5W at 12V). HDMI is the default audio device; the XMOS/TAS5719 path drives the onboard powered speaker outputs.

The XMOS must be explicitly brought out of reset via GPIO before audio works:
```bash
echo 349 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio349/direction
echo 0 > /sys/class/gpio/gpio349/value   # assert reset
echo 1 > /sys/class/gpio/gpio349/value   # release reset
```
GPIO 341 controls mic input selection (0 = microphone, 1 = loopback).

These are managed by `atomicpi-hold-xmos.service` and `atomicpi-hold-mic.service` from [slact/atomicpi-utils](https://github.com/slact/atomicpi-utils).

**I2C / SPI**
The standard kernel I2C/SPI drivers do not map the Atomic Pi's GPIO-bitbanged buses correctly. Two out-of-tree kernel modules are required:
- [digitalloggers/i2c-gpio-custom](https://github.com/digitalloggers/i2c-gpio-custom)
- [digitalloggers/spi-gpio-custom](https://github.com/digitalloggers/spi-gpio-custom)

These are needed for the BNO055 IMU and onboard RTC.

## Known Hardware Quirks

| Issue | Fix |
|---|---|
| Board hangs on shutdown/reboot | Blacklist `dw_dmac` and `dw_dmac_core` kernel modules |
| CMOS reset button near edge | Easily triggered accidentally; corrupts eMMC boot partitions |
| SD card is on USB bus | `/dev/mmcblk0` is eMMC; SD appears as USB mass storage |
| Powered USB hub required | Without it, USB devices (including SD adapter) behave erratically |

Blacklist config (`/etc/modprobe.d/blacklist-atomicpi.conf`):
```
blacklist dw_dmac
blacklist dw_dmac_core
```

## Build Approach

Standard Debian amd64 `debootstrap` into a raw disk image, then `dd` to eMMC:

```
dd if=atomicpi-debian.img of=/dev/mmcblk0 bs=1024k oflag=dsync status=progress
```

Image layout: GPT with an EFI System Partition (FAT32) + root ext4 partition. GRUB EFI bootloader.

## Upstream Sources

| Repo | Purpose |
|---|---|
| [slact/atomicpi-utils](https://github.com/slact/atomicpi-utils) | XMOS + mic GPIO hold services, GPIO pin library |
| [embolon/AtomicPi_Ubuntu_Patch](https://github.com/embolon/AtomicPi_Ubuntu_Patch) | `dw_dmac` blacklist + sysctl performance tweaks |
| [digitalloggers/i2c-gpio-custom](https://github.com/digitalloggers/i2c-gpio-custom) | Out-of-tree I2C GPIO kernel module |
| [digitalloggers/spi-gpio-custom](https://github.com/digitalloggers/spi-gpio-custom) | Out-of-tree SPI GPIO kernel module |
| [ezbe/Atomic-Pi-Tools](https://github.com/ezbe/Atomic-Pi-Tools) | Post-install deployment scripts + systemd services |
| [digital-loggers.com/api_faqs.html](https://www.digital-loggers.com/api_faqs.html) | Official hardware FAQ |
| [digital-loggers.com/downloads](https://www.digital-loggers.com/downloads/) | Official OS images (reference/comparison) |

## Intended Repository Structure

```
build.sh                  # top-level orchestrator
config                    # build-time variables (Debian release, image size, etc.)
scripts/
  01-debootstrap.sh       # base Debian rootfs
  02-kernel.sh            # linux-image + GRUB EFI
  03-hardware.sh          # dw_dmac blacklist, GPIO modules
  04-audio.sh             # XMOS service install, ALSA config
  05-image.sh             # partition image, copy rootfs, install bootloader
files/
  blacklist-atomicpi.conf
  atomicpi-hold-xmos.service
  atomicpi-hold-mic.service
  asound.conf             # set XMOS USB audio as default ALSA device
patches/                  # any kernel or package patches needed
```

## Build Commands

```bash
sudo ./build.sh           # full build, produces atomicpi-debian.img
sudo ./build.sh --stage 4 # run a single stage for iteration
```

Build requires: `debootstrap`, `parted`, `dosfstools`, `grub-efi-amd64`, `qemu-user-static` (if cross-building), `make`, `gcc`, `linux-headers`.
