# atomicpi-profile.sh — Armbian extension for Atomic Pi package injection.
# Enabled via ENABLE_EXTENSIONS="atomicpi-profile" in config-atomicpi-common.conf.
#
# Hook naming: function <hookname>__<extension_name>() { ... }
# Armbian calls hooks in registration order; double-underscore separates hook
# from the extension name so multiple extensions can use the same hook safely.

function post_aggregate_packages__atomicpi_add_packages() {
    display_alert "Atomic Pi" "Injecting Atomic Pi package set" "info"

    # Core utilities
    PACKAGE_LIST_ADDITIONAL+=" \
        openssh-server sudo vim git curl wget tmux \
        htop iotop lm-sensors lshw \
        usbutils pciutils ethtool smartmontools \
        avahi-daemon"

    # Hardware / bus tools
    PACKAGE_LIST_ADDITIONAL+=" \
        i2c-tools alsa-utils \
        dkms build-essential"

    # Non-free firmware: Realtek RTL8111G, MediaTek RT5572 WiFi, misc BT
    PACKAGE_LIST_ADDITIONAL+=" \
        firmware-linux firmware-misc-nonfree \
        firmware-realtek firmware-mediatek"

    # Network security baseline
    PACKAGE_LIST_ADDITIONAL+=" nftables fail2ban unattended-upgrades"

    # Container runtime — Podman preferred (in Debian repos, no external repo needed)
    PACKAGE_LIST_ADDITIONAL+=" podman"
}

function post_build_image__atomicpi_manifest() {
    display_alert "Atomic Pi" "Image complete: ${FINAL_IMAGE_FILE:-unknown}" "info"
}
