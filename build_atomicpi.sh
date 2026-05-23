#!/usr/bin/env bash
# Build an Armbian image for the Atomic Pi.
# Clones (or updates) the Armbian build framework, then runs it with our
# userpatches and config overlay.
#
# Usage:
#   ./build_atomicpi.sh [minimal|server]   (default: minimal)
#   ./build_atomicpi.sh --update-armbian   (pull latest Armbian build framework)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARMBIAN_DIR="${REPO_DIR}/armbian-build"
CONFIG="${1:-minimal}"

if [[ "$CONFIG" == "--update-armbian" ]]; then
    cd "${ARMBIAN_DIR}" && git pull
    echo "Armbian build framework updated."
    exit 0
fi

if [[ ! "$CONFIG" =~ ^(minimal|server)$ ]]; then
    echo "Usage: $0 [minimal|server]"
    exit 1
fi

# ── clone Armbian build framework if needed ───────────────────────────────────
if [[ ! -d "${ARMBIAN_DIR}" ]]; then
    echo "Cloning Armbian build framework..."
    git clone --depth=1 https://github.com/armbian/build "${ARMBIAN_DIR}"
fi

# ── run Armbian compile ───────────────────────────────────────────────────────
echo ""
echo "Building Atomic Pi ${CONFIG} image (Debian Trixie)..."
echo "Logs will appear in ${ARMBIAN_DIR}/output/debug/"
echo ""

cd "${ARMBIAN_DIR}"
./compile.sh \
    USERPATCHES_PATH="${REPO_DIR}/armbian/userpatches" \
    @"${REPO_DIR}/armbian/config-atomicpi-${CONFIG}.conf"

echo ""
echo "Image output: ${ARMBIAN_DIR}/output/images/"
