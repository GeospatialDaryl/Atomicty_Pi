#!/usr/bin/env bash
# Post-first-boot verification and optional hardening for the Atomic Pi.
# Run after flashing and booting into the new image.
# Safe to re-run; all checks are idempotent.
#
# Usage: sudo ./firstboot.sh

set -euo pipefail

PASS=0
FAIL=0
WARN=0

ok()   { echo "  [OK]   $*"; ((PASS++)) || true; }
fail() { echo "  [FAIL] $*"; ((FAIL++)) || true; }
warn() { echo "  [WARN] $*"; ((WARN++)) || true; }

echo "========================================"
echo " Atomic Pi First-Boot Verification"
echo "========================================"

# ── XMOS audio service ────────────────────────────────────────────────────────
echo ""
echo "[ Audio ]"
if systemctl is-active --quiet atomicpi-hold-xmos.service; then
    ok "atomicpi-hold-xmos.service is active"
else
    fail "atomicpi-hold-xmos.service is NOT active"
    echo "       Try: sudo systemctl start atomicpi-hold-xmos.service"
fi

if systemctl is-active --quiet atomicpi-hold-mic.service; then
    ok "atomicpi-hold-mic.service is active"
else
    fail "atomicpi-hold-mic.service is NOT active"
fi

# Check XMOS card appears in ALSA
if aplay -l 2>/dev/null | grep -qi "xmos"; then
    ok "XMOS audio card visible in ALSA (aplay -l)"
else
    fail "XMOS audio card NOT found — check GPIO 349 and USB enumeration"
    echo "       Run: cat /sys/class/gpio/gpio349/value  (should be 1)"
    echo "       Run: lsusb | grep -i xmos"
fi

# ── GPIO 349 state ────────────────────────────────────────────────────────────
echo ""
echo "[ GPIO ]"
if [[ -f /sys/class/gpio/gpio349/value ]]; then
    VAL=$(cat /sys/class/gpio/gpio349/value)
    if [[ "$VAL" == "1" ]]; then
        ok "GPIO 349 (XMOS_RESET) = 1 (released)"
    else
        fail "GPIO 349 (XMOS_RESET) = 0 (still in reset!)"
    fi
else
    warn "GPIO 349 not exported — XMOS service may not have run"
fi

# ── dw_dmac blacklist ─────────────────────────────────────────────────────────
echo ""
echo "[ Kernel modules ]"
if lsmod | grep -q "^dw_dmac"; then
    fail "dw_dmac is loaded — blacklist not effective (shutdown will hang)"
else
    ok "dw_dmac not loaded"
fi

# ── DKMS modules ──────────────────────────────────────────────────────────────
for MOD in i2c-gpio-custom spi-gpio-custom; do
    if lsmod | grep -q "^${MOD//-/_}"; then
        ok "${MOD} loaded"
    else
        warn "${MOD} not loaded (may not be needed until I2C/SPI devices are wired)"
    fi
done

# ── networking ────────────────────────────────────────────────────────────────
echo ""
echo "[ Networking ]"
if ip link show | grep -q "eno\|enp\|eth"; then
    ok "Ethernet interface present"
else
    warn "No wired ethernet interface found"
fi

if ip link show | grep -q "wlan\|wlp"; then
    ok "WiFi interface present (rt2800usb)"
else
    warn "No WiFi interface — firmware-mediatek may be missing"
fi

# ── firmware ──────────────────────────────────────────────────────────────────
echo ""
echo "[ Firmware ]"
for pkg in firmware-realtek firmware-mediatek; do
    if dpkg -l "$pkg" &>/dev/null; then
        ok "$pkg installed"
    else
        warn "$pkg not installed"
    fi
done

# ── PulseAudio sink name (informational) ─────────────────────────────────────
echo ""
echo "[ PulseAudio sinks ]"
echo "  (run as user, not root — pactl requires user session)"
if command -v pactl &>/dev/null; then
    warn "Run 'pactl list sinks short' as your user to verify XMOS sink name"
    warn "Update /etc/pulse/default-sink.pa if the sink name differs"
fi

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Results: ${PASS} passed, ${WARN} warnings, ${FAIL} failed"
echo "========================================"
[[ $FAIL -gt 0 ]] && exit 1 || exit 0
