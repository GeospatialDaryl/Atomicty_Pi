#!/usr/bin/env bash
# customize-image.sh — Atomic Pi image customization hook.
# Called by Armbian inside the image chroot after package installation.
# Static config files are placed via overlay/; this script handles
# runtime steps that require the installed environment.
#
# Environment: $RELEASE, $BOARD, $DISTRIBUTION, $ARCH, $DESKTOP_ENVIRONMENT
# Overlay path inside chroot: /tmp/overlay/

set -euo pipefail

# Armbian passes these as positional args (customize.sh:34), not env vars.
RELEASE="${1:-}"
LINUXFAMILY="${2:-}"
BOARD="${3:-}"
BUILD_DESKTOP="${4:-}"
ARCH="${5:-}"

echo ">>> Atomic Pi customize-image: start (${RELEASE} / ${BOARD})"

# ── 1. Apply overlay ──────────────────────────────────────────────────────────
# Copies the userpatches/overlay/ tree into the image root.
# Covers: modprobe blacklist, sysctl, udev rules, asound.conf,
#         systemd services (XMOS, mic, firstboot), atomicpi profile marker.
if [[ -d /tmp/overlay ]]; then
    rsync -a /tmp/overlay/ /
    echo ">>> [1] Overlay applied"
else
    echo ">>> [1] WARNING: /tmp/overlay not found — overlay files not applied"
fi

# ── 2. Set permissions ────────────────────────────────────────────────────────
chmod 755 /usr/local/sbin/atomicpi-firstboot
chmod 755 /usr/local/sbin/atomicpi-xmos-reset
echo ">>> [2] Permissions set"

# ── 3. Enable systemd services ────────────────────────────────────────────────
systemctl enable atomicpi-hold-xmos.service
systemctl enable atomicpi-hold-mic.service
systemctl enable atomicpi-firstboot.service
systemctl enable ssh          2>/dev/null || systemctl enable sshd 2>/dev/null || true
systemctl enable avahi-daemon 2>/dev/null || true
systemctl enable nftables     2>/dev/null || true
systemctl enable fail2ban     2>/dev/null || true
echo ">>> [3] Systemd services enabled"

# ── 4. Security defaults ─────────────────────────────────────────────────────
# Disable password auth in SSH — keys only. Image users must set a key via
# preset-firstrun.sh or manually on first boot.
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
echo ">>> [4] SSH hardened (password auth disabled)"

# ── 5. DKMS: i2c-gpio-custom and spi-gpio-custom ─────────────────────────────
# Out-of-tree GPIO modules for the Z8350's bitbanged I2C/SPI buses.
# Skipped when kernel headers are absent (minimal/server/desktop profiles).
# Headers are only present in the dev profile (INSTALL_HEADERS=yes).
KVER=$(ls /lib/modules/ | tail -1)

if [[ ! -d "/lib/modules/${KVER}/build" ]]; then
    echo ">>> [5] DKMS skipped — kernel headers not installed (non-dev profile)"
    echo ">>> Atomic Pi customize-image: complete"
    exit 0
fi

for MODULE in i2c-gpio-custom spi-gpio-custom; do
    VERSION=1.0
    DKMS_SRC=/usr/src/${MODULE}-${VERSION}
    mkdir -p "${DKMS_SRC}"

    git clone --depth=1 "https://github.com/digitalloggers/${MODULE}" \
        "/tmp/${MODULE}-src"

    cp /tmp/${MODULE}-src/Makefile "${DKMS_SRC}/"
    find /tmp/${MODULE}-src -maxdepth 1 \( -name "*.c" -o -name "*.h" \) \
        -exec cp {} "${DKMS_SRC}/" \;

    SUBDIR=$([ "$MODULE" = "i2c-gpio-custom" ] && echo "i2c" || echo "spi")
    cat > "${DKMS_SRC}/dkms.conf" <<DKMSEOF
PACKAGE_NAME="${MODULE}"
PACKAGE_VERSION="${VERSION}"
BUILT_MODULE_NAME[0]="${MODULE}"
DEST_MODULE_LOCATION[0]="/kernel/drivers/${SUBDIR}/"
AUTOINSTALL="yes"
DKMSEOF

    dkms add     -m "${MODULE}" -v "${VERSION}"
    dkms build   -m "${MODULE}" -v "${VERSION}" -k "${KVER}"
    dkms install -m "${MODULE}" -v "${VERSION}" -k "${KVER}"
    echo "${MODULE}" >> /etc/modules-load.d/atomicpi.conf
done

echo ">>> [5] DKMS GPIO modules installed (kernel ${KVER})"
echo ">>> Atomic Pi customize-image: complete"
