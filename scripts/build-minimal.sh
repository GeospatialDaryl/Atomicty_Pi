#!/usr/bin/env bash
# Build the Atomic Pi minimal image (headless, systemd-networkd, ~3.5 GB).
set -euo pipefail

ARMBIAN_BUILD_DIR="${ARMBIAN_BUILD_DIR:-$HOME/src/armbian-build}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USERPATCHES="${PROJECT_DIR}/armbian/userpatches"

if [[ ! -d "$ARMBIAN_BUILD_DIR" ]]; then
    echo "Cloning Armbian build framework to ${ARMBIAN_BUILD_DIR}..."
    git clone --depth=1 https://github.com/armbian/build "$ARMBIAN_BUILD_DIR"
fi

cd "$ARMBIAN_BUILD_DIR"
./compile.sh build \
    USERPATCHES_PATH="$USERPATCHES" \
    atomicpi-minimal
