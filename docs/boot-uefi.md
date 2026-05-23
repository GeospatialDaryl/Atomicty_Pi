# Boot Notes

## BIOS / UEFI

- Press **Del** or **Tab** at the AAEON BIOS splash to enter firmware settings.
- AMI-type BIOS interface; standard menu navigation.
- **Legacy BIOS / MBR boot is not supported.** The image must use GPT + EFI partition.
- Armbian's `uefi-x86` target produces a correct GPT/EFI image automatically.

## Boot order

The default BIOS boot order after a CMOS reset **may prioritise PXE/network boot** over eMMC.
If the board doesn't boot from eMMC after flashing, enter BIOS and move eMMC to the top of the boot order.

To enter BIOS for boot order change:
1. Connect keyboard and monitor (or serial console on CN10).
2. Power on; press **Del** immediately at splash.
3. Navigate to Boot → Boot Priority Order.
4. Move the eMMC device above PXE/network entries.
5. Save and exit.

## Serial console access

Useful when HDMI is unavailable or for early boot debugging:

- **Connector:** CN10 (3-pin header, board edge)
- **Level:** 3.3V TTL — use a USB/TTL adapter (CP2102, CH340, PL2303)
- **Speed:** 115200 baud, 8N1
- **Pinout:** Pin 1 = TX (board → adapter RX), Pin 2 = RX, Pin 3 = GND
- GRUB is configured to echo to both VGA and serial, so you get a boot menu on both.

## eMMC device path

The eMMC is always `/dev/mmcblk0` on the Atomic Pi.
The SD card, if inserted, appears as a USB mass storage device (`/dev/sdX`), **not** as `/dev/mmcblk1`.

## Booting from USB/SD for installation

1. Write the Armbian image to a USB drive using `scripts/flash-usb.sh`.
2. Plug the USB drive into the Atomic Pi.
3. Use a **powered USB hub** — the board draws more current than unpowered USB can reliably supply.
4. Power on; if USB doesn't boot automatically, enter BIOS and select USB as boot device.
5. Once booted, run `scripts/flash-emmc.sh` to write to internal eMMC.

## First boot from eMMC

Armbian performs first-boot setup automatically:
- Root filesystem is expanded to fill the eMMC partition.
- SSH host keys are generated.
- System hostname and locale are configured (or prompted).

Default credentials set by Armbian first-run wizard:
- Root password: prompted on first SSH/console login.
- User: created interactively.

Our `scripts/firstboot.sh` verifies audio, GPIO, and networking after this step.
