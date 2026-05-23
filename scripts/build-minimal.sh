#!/usr/bin/env bash
# Build the Atomic Pi minimal image (headless, systemd-networkd, ~3.5 GB).
set -euo pipefail

ARMBIAN_BUILD_DIR="${ARMBIAN_BUILD_DIR:-$HOME/src/armbian-build}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUR_UP="${PROJECT_DIR}/armbian/userpatches"
ARMBIAN_UP="${ARMBIAN_BUILD_DIR}/userpatches"

if [[ ! -d "$ARMBIAN_BUILD_DIR" ]]; then
    echo "Cloning Armbian build framework to ${ARMBIAN_BUILD_DIR}..."
    git clone --depth=1 https://github.com/armbian/build "$ARMBIAN_BUILD_DIR"
fi

# Symlink our userpatches tree into Armbian's userpatches dir.
# Armbian hardcodes USERPATCHES_PATH=${SRC}/userpatches (read-only after init),
# so USERPATCHES_PATH=... on the cmdline is overridden. Symlinks are the fix.
mkdir -p "$ARMBIAN_UP"
for item in "$OUR_UP"/*; do
    ln -sf "$item" "$ARMBIAN_UP/$(basename "$item")"
done
echo "Userpatches symlinked: ${ARMBIAN_UP}"

cd "$ARMBIAN_BUILD_DIR"
./compile.sh build atomicpi-minimal
