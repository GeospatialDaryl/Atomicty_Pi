#!/bin/bash
# Armbian customize-image.sh — Atomic Pi hardware layer
#
# Called by Armbian build framework after the base image is assembled.
# Runs as root inside the image chroot.
# Environment: $RELEASE, $BOARD, $DISTRIBUTION, $ARCH, $DESKTOP_ENVIRONMENT
#
# This script applies all Atomic Pi-specific configuration on top of the
# generic Armbian uefi-x86 image:
#   1. dw_dmac blacklist          (prevents shutdown/reboot hang)
#   2. sysctl performance tweaks  (2 GB RAM optimisations)
#   3. udev GPIO rules            (audio group owns GPIO chips)
#   4. XMOS audio systemd services (brings powered speaker outputs up at boot)
#   5. ALSA default device config  (XMOS as default, HDMI as fallback)
#   6. Non-free firmware           (Realtek, MediaTek, CSR Bluetooth)
#   7. DKMS GPIO modules           (i2c-gpio-custom, spi-gpio-custom)

set -euo pipefail

echo ">>> Atomic Pi hardware layer: starting"

# ── 1. dw_dmac blacklist ──────────────────────────────────────────────────────
# The DesignWare DMA driver conflicts with the Z8350 HSUART DMA engine and
# causes the board to hang on every shutdown/reboot without this blacklist.
cat > /etc/modprobe.d/blacklist-atomicpi.conf <<'EOF'
# dw_dmac / dw_dmac_core conflict with Z8350 HSUART DMA → hang on shutdown
blacklist dw_dmac
blacklist dw_dmac_core
EOF
echo ">>> [1/7] dw_dmac blacklist installed"

# ── 2. sysctl tweaks ─────────────────────────────────────────────────────────
cat > /etc/sysctl.d/99-atomicpi.conf <<'EOF'
# Atomic Pi: optimise for 2 GB RAM
vm.swappiness=10
vm.dirty_background_ratio=5
vm.dirty_ratio=10
fs.inotify.max_user_watches=524288
EOF
echo ">>> [2/7] sysctl tweaks installed"

# ── 3. udev GPIO rules ────────────────────────────────────────────────────────
# Grant audio group ownership of GPIO chips so the XMOS service can run
# without root after initial setup if desired.
cat > /etc/udev/rules.d/99-atomicpi-gpio.rules <<'EOF'
# Atomic Pi: audio group owns GPIO chips
# gpiochip1 pin 8 (sysfs 349) = XMOS_RESET
# gpiochip1 pin ? (sysfs 341) = AU_MIC_SEL
SUBSYSTEM=="gpio", KERNEL=="gpiochip[0-3]", GROUP="audio", MODE="0660"
SUBSYSTEM=="gpio", KERNEL=="gpio*", GROUP="audio", MODE="0660"
EOF
echo ">>> [3/7] udev GPIO rules installed"

# ── 4. XMOS audio systemd services ───────────────────────────────────────────
# atomicpi-hold-xmos: toggles GPIO 349 to bring the XMOS xCORE out of reset.
# Must run before the sound subsystem so the USB audio device is present
# when PulseAudio/PipeWire starts.
cat > /etc/systemd/system/atomicpi-hold-xmos.service <<'EOF'
[Unit]
Description=Atomic Pi — release XMOS audio processor from reset
Documentation=https://www.digital-loggers.com/api_faqs.html
After=sysinit.target local-fs.target
Before=sound.target pulseaudio.service pipewire.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sh -c 'echo 349 > /sys/class/gpio/export 2>/dev/null || true'
ExecStartPre=/bin/sh -c 'echo out > /sys/class/gpio/gpio349/direction'
ExecStartPre=/bin/sh -c 'echo 0 > /sys/class/gpio/gpio349/value'
ExecStartPre=/bin/sh -c 'sleep 0.1'
ExecStart=/bin/sh    -c 'echo 1 > /sys/class/gpio/gpio349/value'
ExecStop=/bin/sh     -c 'echo 349 > /sys/class/gpio/unexport 2>/dev/null || true'

[Install]
WantedBy=multi-user.target
EOF

# atomicpi-hold-mic: sets GPIO 341 (AU_MIC_SEL) to 0 = microphone input.
# Set to 1 for loopback. Depends on XMOS being up first.
cat > /etc/systemd/system/atomicpi-hold-mic.service <<'EOF'
[Unit]
Description=Atomic Pi — configure XMOS microphone input (GPIO 341)
Documentation=https://www.digital-loggers.com/api_faqs.html
After=atomicpi-hold-xmos.service
Requires=atomicpi-hold-xmos.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sh -c 'echo 341 > /sys/class/gpio/export 2>/dev/null || true'
ExecStartPre=/bin/sh -c 'echo out > /sys/class/gpio/gpio341/direction'
ExecStart=/bin/sh    -c 'echo 0 > /sys/class/gpio/gpio341/value'
ExecStop=/bin/sh     -c 'echo 341 > /sys/class/gpio/unexport 2>/dev/null || true'

[Install]
WantedBy=multi-user.target
EOF

systemctl enable atomicpi-hold-xmos.service
systemctl enable atomicpi-hold-mic.service
echo ">>> [4/7] XMOS systemd services installed and enabled"

# ── 5. ALSA configuration ─────────────────────────────────────────────────────
# Default ALSA device is the XMOS USB audio card ("XMOS").
# HDMI remains accessible as pcm.hdmi_out.
# If XMOS card name differs on your kernel, check with: aplay -l
cat > /etc/asound.conf <<'EOF'
# Atomic Pi ALSA config
# Card 0: HDA Intel HDMI  (default HDMI output)
# Card 1: XMOS USB Audio  (powered speaker outputs via TI TAS5719)
#
# Named alias for explicit access: aplay -D xmos file.wav
pcm.xmos {
    type hw
    card "XMOS"
}
ctl.xmos {
    type hw
    card "XMOS"
}

pcm.hdmi_out {
    type hw
    card "Intel"
    device 3
}

# Default = XMOS powered outputs.
# Swap to "Intel"/device 3 to default to HDMI.
pcm.!default {
    type plug
    slave.pcm "hw:XMOS,0"
}
ctl.!default {
    type hw
    card "XMOS"
}
EOF
echo ">>> [5/7] ALSA config installed (default: XMOS powered outputs)"

# ── 6. Non-free firmware ──────────────────────────────────────────────────────
# RT5572 WiFi (rt2800usb), Realtek RTL8111G ethernet, CSR8510 Bluetooth
apt-get install -y --no-install-recommends \
    firmware-realtek \
    firmware-mediatek \
    firmware-misc-nonfree \
    alsa-utils
echo ">>> [6/7] Non-free firmware installed"

# ── 7. DKMS: i2c-gpio-custom and spi-gpio-custom ─────────────────────────────
# These out-of-tree kernel modules are needed for the GPIO-bitbanged I2C and
# SPI buses that connect the BNO055 IMU and onboard RTC.
# Modules are built against the currently installed kernel and will rebuild
# automatically on kernel upgrades via DKMS.
apt-get install -y --no-install-recommends dkms git build-essential

for MODULE in i2c-gpio-custom spi-gpio-custom; do
    VERSION=1.0
    DKMS_SRC=/usr/src/${MODULE}-${VERSION}
    mkdir -p ${DKMS_SRC}

    git clone --depth=1 https://github.com/digitalloggers/${MODULE} /tmp/${MODULE}-src
    # Copy source files (Makefile + *.c)
    cp /tmp/${MODULE}-src/Makefile ${DKMS_SRC}/
    find /tmp/${MODULE}-src -maxdepth 1 \( -name "*.c" -o -name "*.h" \) \
        -exec cp {} ${DKMS_SRC}/ \;

    SUBDIR=$([ "$MODULE" = "i2c-gpio-custom" ] && echo "i2c" || echo "spi")
    cat > ${DKMS_SRC}/dkms.conf <<DKMSEOF
PACKAGE_NAME="${MODULE}"
PACKAGE_VERSION="${VERSION}"
BUILT_MODULE_NAME[0]="${MODULE}"
DEST_MODULE_LOCATION[0]="/kernel/drivers/${SUBDIR}/"
AUTOINSTALL="yes"
DKMSEOF

    KVER=$(ls /lib/modules/ | tail -1)
    dkms add    -m ${MODULE} -v ${VERSION}
    dkms build  -m ${MODULE} -v ${VERSION} -k ${KVER}
    dkms install -m ${MODULE} -v ${VERSION} -k ${KVER}
    echo "${MODULE}" >> /etc/modules-load.d/atomicpi.conf
done

echo ">>> [7/7] DKMS GPIO modules installed"
echo ">>> Atomic Pi hardware layer: complete"
