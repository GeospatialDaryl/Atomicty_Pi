#!/usr/bin/env bash
# Mount an Armbian image for inspection or manual modification.
# Usage: sudo ./scripts/mount-image.sh <image.img> [mountpoint]
#        sudo ./scripts/mount-image.sh --umount [mountpoint]

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: run as root (sudo $0 ...)"
    exit 1
fi

UMOUNT=false
[[ "${1:-}" == "--umount" ]] && { UMOUNT=true; shift; }

MOUNTPOINT="${2:-/mnt/atomicpi-image}"
IMAGE="${1:-}"

if $UMOUNT; then
    echo "Unmounting ${MOUNTPOINT}..."
    umount "${MOUNTPOINT}/boot/efi" 2>/dev/null || true
    umount "${MOUNTPOINT}"           2>/dev/null || true
    LOOP=$(losetup -j "${IMAGE:-}" 2>/dev/null | cut -d: -f1 || true)
    [[ -n "$LOOP" ]] && losetup -d "$LOOP" 2>/dev/null || true
    echo "Done."
    exit 0
fi

if [[ -z "$IMAGE" || ! -f "$IMAGE" ]]; then
    echo "Usage: $0 <image.img> [mountpoint]"
    echo "       $0 --umount <image.img> [mountpoint]"
    exit 1
fi

echo "Attaching ${IMAGE}..."
LOOP=$(losetup --find --partscan --show "$IMAGE")
echo "Loop device: ${LOOP}"
sleep 0.5

mkdir -p "${MOUNTPOINT}"
mount "${LOOP}p2" "${MOUNTPOINT}"
mkdir -p "${MOUNTPOINT}/boot/efi"
mount "${LOOP}p1" "${MOUNTPOINT}/boot/efi"

echo ""
echo "Mounted at: ${MOUNTPOINT}"
echo "EFI at:     ${MOUNTPOINT}/boot/efi"
echo ""
echo "To unmount: sudo $0 --umount ${IMAGE} ${MOUNTPOINT}"
