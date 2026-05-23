#!/usr/bin/env bash
# QEMU smoke test for the Atomic Pi Armbian image.
# Boots the image under QEMU/KVM with OVMF (UEFI) firmware and checks that
# it reaches a login prompt within a timeout. No actual Atomic Pi hardware needed.
#
# Requirements: qemu-system-x86_64, ovmf, expect
#   sudo apt-get install qemu-system-x86 ovmf expect
#
# Usage: ./scripts/qemu-smoke-test.sh <image.img[.xz]>

set -euo pipefail

IMAGE="${1:-}"
TIMEOUT=180   # seconds to wait for login prompt
OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"
OVMF_VARS="/usr/share/OVMF/OVMF_VARS.fd"

if [[ -z "$IMAGE" ]]; then
    echo "Usage: $0 <image.img[.xz]>"
    exit 1
fi

for dep in qemu-system-x86_64 expect; do
    command -v "$dep" &>/dev/null || {
        echo "ERROR: $dep not found. Install: sudo apt-get install qemu-system-x86 expect"
        exit 1
    }
done

[[ -f "$OVMF_CODE" ]] || { echo "ERROR: OVMF not found at $OVMF_CODE. Install: sudo apt-get install ovmf"; exit 1; }

# Decompress if needed
WORK_IMAGE="$IMAGE"
if [[ "$IMAGE" == *.xz ]]; then
    WORK_IMAGE="${IMAGE%.xz}"
    echo "Decompressing ${IMAGE}..."
    xz -dk "$IMAGE"
fi

echo "Booting ${WORK_IMAGE} under QEMU (timeout: ${TIMEOUT}s)..."
echo "QEMU serial output will appear below. Ctrl-C to abort."
echo ""

# OVMF vars copy (QEMU writes EFI variables here)
VARS_TMP=$(mktemp /tmp/ovmf-vars-XXXXXX.fd)
cp "$OVMF_VARS" "$VARS_TMP"
trap "rm -f $VARS_TMP" EXIT

expect -c "
    set timeout ${TIMEOUT}
    spawn qemu-system-x86_64 \
        -enable-kvm \
        -m 2048 \
        -smp 4 \
        -drive if=pflash,format=raw,readonly=on,file=${OVMF_CODE} \
        -drive if=pflash,format=raw,file=${VARS_TMP} \
        -drive file=${WORK_IMAGE},format=raw,if=virtio \
        -net nic,model=virtio \
        -net user \
        -serial stdio \
        -display none \
        -no-reboot

    expect {
        \"login:\" {
            send_user \"\n\[PASS\] Login prompt reached\n\"
            exit 0
        }
        timeout {
            send_user \"\n\[FAIL\] Timed out after ${TIMEOUT}s waiting for login prompt\n\"
            exit 1
        }
        eof {
            send_user \"\n\[FAIL\] QEMU exited unexpectedly\n\"
            exit 1
        }
    }
"
