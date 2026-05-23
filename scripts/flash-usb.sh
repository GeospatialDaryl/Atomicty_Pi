#!/usr/bin/env bash
# Write an Atomic Pi image to a USB drive or SD card for booting/flashing.
# This is the tool you use on your workstation before touching the board.
#
# Usage: sudo ./scripts/flash-usb.sh <image.img[.xz]> <device>
# Example: sudo ./scripts/flash-usb.sh atomicpi-minimal.img.xz /dev/sdb
#
# WARNING: double-check <device> with `lsblk` before running — wrong device
# will destroy data on that disk.

set -euo pipefail

IMAGE="${1:-}"
DEVICE="${2:-}"

if [[ -z "$IMAGE" || -z "$DEVICE" ]]; then
    echo "Usage: $0 <image.img[.xz]> <device>"
    echo "       $0 atomicpi-minimal.img.xz /dev/sdb"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo $0 ...)"
    exit 1
fi

if [[ ! -b "$DEVICE" ]]; then
    echo "ERROR: $DEVICE is not a block device"
    exit 1
fi

# Safety check: refuse to write to a mounted device
if mount | grep -q "^${DEVICE}"; then
    echo "ERROR: ${DEVICE} is currently mounted — unmount first"
    exit 1
fi

echo "Target device: $DEVICE"
lsblk "$DEVICE"
echo ""
read -r -p "Write ${IMAGE} to ${DEVICE}? This will erase the device. [yes/N] " CONFIRM
[[ "$CONFIRM" != "yes" ]] && { echo "Aborted."; exit 0; }

echo "Writing..."
if [[ "$IMAGE" == *.xz ]]; then
    xzcat "$IMAGE" | dd of="$DEVICE" bs=4M oflag=dsync status=progress
else
    dd if="$IMAGE" of="$DEVICE" bs=4M oflag=dsync status=progress
fi

sync
echo "Done. Safely eject ${DEVICE} and boot the Atomic Pi from it."
