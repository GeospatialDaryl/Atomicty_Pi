#!/usr/bin/env bash
# Write the Atomic Pi image to internal eMMC.
# Run this ON THE ATOMIC PI itself, booted from USB/SD (not from eMMC).
#
# Usage: sudo ./scripts/flash-emmc.sh <image.img[.xz]>
#
# The image can be fetched from a local USB drive, network share, or HTTP.
# eMMC device is /dev/mmcblk0 — verify with `lsblk` before proceeding.
#
# CAUTION: accidentally pressing the CMOS reset button on the board edge
# during this operation will corrupt the eMMC. Handle the board carefully.

set -euo pipefail

IMAGE="${1:-}"
EMMC="/dev/mmcblk0"

if [[ -z "$IMAGE" ]]; then
    echo "Usage: $0 <image.img[.xz]>"
    echo "       $0 /media/usb/atomicpi-minimal.img.xz"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo $0 ...)"
    exit 1
fi

if [[ ! -b "$EMMC" ]]; then
    echo "ERROR: ${EMMC} not found — are you running this on the Atomic Pi?"
    echo "       If booted from eMMC, you cannot flash eMMC in-place."
    exit 1
fi

# Refuse to write if we're currently booted from eMMC
BOOT_DEV=$(findmnt -n -o SOURCE / | sed 's/p[0-9]*$//')
if [[ "$BOOT_DEV" == "$EMMC" ]]; then
    echo "ERROR: currently booted from ${EMMC} — boot from USB/SD first"
    exit 1
fi

echo "eMMC device: $EMMC"
lsblk "$EMMC"
echo ""
echo "This will ERASE ALL DATA on the Atomic Pi's internal storage."
read -r -p "Flash ${IMAGE} to ${EMMC}? [yes/N] " CONFIRM
[[ "$CONFIRM" != "yes" ]] && { echo "Aborted."; exit 0; }

echo "Flashing — do not disturb the board..."
if [[ "$IMAGE" == *.xz ]]; then
    xzcat "$IMAGE" | dd of="$EMMC" bs=1024k oflag=dsync status=progress
else
    dd if="$IMAGE" of="$EMMC" bs=1024k oflag=dsync status=progress
fi

sync
echo ""
echo "Flash complete. Remove the USB/SD boot media and reboot."
echo "First boot will expand the root filesystem automatically (Armbian)."
