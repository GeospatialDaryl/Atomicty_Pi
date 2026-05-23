# Atomic Pi Hardware Reference

## Core specs

| Component | Detail |
|---|---|
| CPU | Intel Atom x5-Z8350, 4-core, 1.44 GHz (burst 1.92 GHz), Cherry Trail |
| Architecture | x86-64 only — 32-bit images will not boot |
| RAM | 2 GB LPDDR3 |
| Storage | 16 GB eMMC at `/dev/mmcblk0` |
| Boot firmware | AMI UEFI (AAEON BIOS splash); press **Del** or **Tab** to enter |
| Serial console | CN10, 3.3V TTL, 115200 8N1. Pins: 1=TX 2=RX 3=GND |

## Networking

| Interface | Chip | Driver | Notes |
|---|---|---|---|
| Ethernet | Realtek RTL8111G | `r8169` | Mainline kernel, works immediately |
| WiFi | MediaTek RT5572 | `rt2800usb` | USB bus; needs `firmware-mediatek` |
| Bluetooth | Qualcomm CSR8510 | `btusb` | USB bus |

## Audio chain

```
XMOS xCORE (USB Audio 2.0) ──I2S──► TI TAS5719 class-D amp ──► Powered speaker outputs
                                                                  1.5 W/ch @ 5 V
                                                                  5.0 W/ch @ 12 V
```

- **HDMI** is the default audio device; appears as card 0 in ALSA.
- **XMOS/TAS5719** is card 1 ("XMOS") — drives the onboard powered outputs.
- XMOS starts in reset at power-on. **GPIO 349** must be deasserted to bring it up.
- `atomicpi-hold-xmos.service` handles this at boot.

## GPIO reference (audio-relevant)

| sysfs # | gpiochip | Pin | Signal | Direction | Notes |
|---|---|---|---|---|---|
| 349 | gpiochip1 | 8 | XMOS_RESET | Output | 0=reset, 1=run |
| 341 | gpiochip1 | ? | AU_MIC_SEL | Output | 0=mic, 1=loopback |

## I2C / SPI

Standard kernel drivers do not expose the Z8350's GPIO-bitbanged buses correctly.
Two out-of-tree DKMS modules are required:

- `i2c-gpio-custom` — [github.com/digitalloggers/i2c-gpio-custom](https://github.com/digitalloggers/i2c-gpio-custom)
- `spi-gpio-custom` — [github.com/digitalloggers/spi-gpio-custom](https://github.com/digitalloggers/spi-gpio-custom)

Connected I2C devices:

| Device | Address | Notes |
|---|---|---|
| Bosch BNO055 | 0x28 or 0x29 | 9-DOF IMU (accel, gyro, magnetometer) |
| RTC | TBD | Onboard clock/calendar module |

## Power

- **5V input** via breakout header (not USB-C): minimum 3A recommended, 5A for stable USB operation.
- **12V optional**: needed for full 5W/ch audio output power. Most users run on 5V only.
- USB peripherals can draw phantom power from a hub even after the board shuts down.

## Known hardware quirks

| Issue | Root cause | Fix |
|---|---|---|
| Hangs on shutdown/reboot | `dw_dmac` conflicts with Z8350 HSUART DMA | Blacklist `dw_dmac` and `dw_dmac_core` |
| CMOS reset button | Located near board edge, easily pressed | Corrupts eMMC boot partitions; handle carefully |
| SD card on USB bus | Genesys Logic SD controller is USB-attached | SD appears as USB mass storage, not `mmcblk1` |
| USB instability | Board draws more than a typical USB port provides | Use a powered hub during installation |
