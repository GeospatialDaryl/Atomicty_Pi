# Hardware Boot Evidence

This document records the commands to run and output to capture for a confirmed
hardware boot. The results feed directly into the Armbian upstream PR.

---

## Step 1 — Capture serial console boot log

Connect CN10 (3.3V TTL, 115200 8N1) before powering on.

```bash
# Option A: screen
screen -L -Logfile ~/atomic-pi-boot.log /dev/ttyUSB0 115200

# Option B: minicom
minicom -C ~/atomic-pi-boot.log -D /dev/ttyUSB0 -b 115200
```

Save the full log from power-on through login prompt. Attach as
`atomic-pi-boot.log` in the PR.

---

## Step 2 — Run on the booted board

SSH in or use the console. Run each block and save output.

### System identity
```bash
uname -a
cat /etc/armbian-release
hostnamectl
```

### Armbian system report (paste URL goes directly in PR)
```bash
armbianmonitor -u
```

### Kernel and drivers
```bash
lsmod | grep -E "r8169|rt2800usb|btusb|i915"
dmesg | grep -iE "dw_dmac|xmos|tas57|r8169|rt2800|btusb|eMMC|mmcblk"
```

### dw_dmac blacklist confirmed
```bash
lsmod | grep dw_dmac    # should return nothing
cat /proc/modules | grep dw_dmac    # should return nothing
```

### Audio
```bash
aplay -l                # should show XMOS card
systemctl status atomicpi-hold-xmos atomicpi-hold-mic
# Test playback:
speaker-test -D hw:XMOS,0 -c 2 -t sine -f 440 -l 1
```

### Networking
```bash
ip link show
iwconfig 2>/dev/null || iw dev
hciconfig -a 2>/dev/null || bluetoothctl show
```

### Storage
```bash
lsblk
# eMMC should be /dev/mmcblk0
# SD card (if inserted) should appear as /dev/sdX, NOT mmcblk1
```

### Services
```bash
systemctl status atomicpi-hold-xmos
systemctl status atomicpi-hold-mic
systemctl status atomicpi-firstboot
```

### Thermal
```bash
cat /sys/class/thermal/thermal_zone*/temp   # divide by 1000 for °C
# Should be < 80000 (80°C) at idle
```

### GPIO
```bash
gpiodetect
gpioinfo gpiochip1 | grep -E "line 8|line 0"
# GPIO 349 = gpiochip1 line 8 (XMOS_RESET, should read 1 = running)
```

---

## Step 3 — Fill in the test matrix

Copy this into a PR comment with results:

```
## Hardware validation — Atomic Pi / Armbian trixie current 6.x

| Test | Result | Notes |
|---|---|---|
| Boots from USB | | |
| Boots from eMMC | | |
| HDMI console | | |
| Serial console ttyS0 | | |
| Ethernet (r8169) | | |
| WiFi (rt2800usb) | | |
| Bluetooth (btusb) | | |
| eMMC at /dev/mmcblk0 | | |
| SD card as USB mass storage | | |
| XMOS service starts, GPIO 349 released | | |
| ALSA shows XMOS card | | |
| Audio plays through powered outputs | | |
| dw_dmac not loaded | | |
| Clean shutdown | | |
| Clean reboot | | |
| USB 2/3 devices recognized | | |
| Thermal < 80°C at idle | | |

armbianmonitor -u URL: <paste here>
Boot log: <attach atomic-pi-boot.log>
```

---

## Step 4 — What to attach to the PR

| Artifact | How to get it |
|---|---|
| `armbianmonitor -u` URL | Run on board, paste URL |
| `atomic-pi-boot.log` | Serial console capture from Step 1 |
| Filled test matrix | Step 3 above, posted as PR comment |
| Photo of running board (optional) | Shows board powered on with Armbian |
