#!/usr/bin/env bash
# Build the Atomic Pi server image (NetworkManager, Podman, dev tools, ~6 GB).
set -euo pipefail

ARMBIAN_BUILD_DIR="${ARMBIAN_BUILD_DIR:-$HOME/src/armbian-build}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUR_UP="${PROJECT_DIR}/armbian/userpatches"
ARMBIAN_UP="${ARMBIAN_BUILD_DIR}/userpatches"

if [[ ! -d "$ARMBIAN_BUILD_DIR" ]]; then
    echo "Cloning Armbian build framework to ${ARMBIAN_BUILD_DIR}..."
    git clone --depth=1 https://github.com/armbian/build "$ARMBIAN_BUILD_DIR"
fi

mkdir -p "$ARMBIAN_UP"
for item in "$OUR_UP"/*; do
    ln -sf "$item" "$ARMBIAN_UP/$(basename "$item")"
done
echo "Userpatches symlinked: ${ARMBIAN_UP}"

cd "$ARMBIAN_BUILD_DIR"

# Replace Armbian's WSL2 dollar-sign emoji with the Eye of Horus.
LOGGING_SH="lib/functions/logging/logging.sh"
if grep -q '💲' "$LOGGING_SH" 2>/dev/null; then
    sed -i 's/💲/𓂀/g' "$LOGGING_SH"
fi

./compile.sh build atomicpi-server
