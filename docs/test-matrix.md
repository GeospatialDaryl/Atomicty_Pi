# Test Matrix

After flashing and first boot, verify each item. Run `scripts/firstboot.sh` for automated checks.

## Boot

| Test | Command / Method | Expected |
|---|---|---|
| Boots from eMMC | Power on, observe console/HDMI | GRUB menu, then Armbian login |
| Serial console | Connect USB/TTL to CN10, 115200 | GRUB + boot messages on serial |
| Root fs expanded | `df -h /` | Shows ~6+ GB free on 7 GB root |
| Correct kernel | `uname -r` | Armbian current-branch kernel |

## Audio (critical path)

| Test | Command | Expected |
|---|---|---|
| XMOS service active | `systemctl status atomicpi-hold-xmos` | `active (exited)` |
| GPIO 349 released | `cat /sys/class/gpio/gpio349/value` | `1` |
| XMOS card in ALSA | `aplay -l` | Line containing "XMOS" |
| Playback via XMOS | `aplay -D xmos /usr/share/sounds/alsa/Front_Left.wav` | Audible from powered outputs |
| ALSA default = XMOS | `aplay /usr/share/sounds/alsa/Front_Left.wav` | Same as above |
| HDMI audio | `aplay -D hdmi_out /usr/share/sounds/alsa/Front_Left.wav` | Audible from HDMI display |
| PulseAudio sink | `pactl list sinks short` (as user) | XMOS sink listed |
| PulseAudio default | `paplay /usr/share/sounds/alsa/Front_Left.wav` (as user) | Audible from powered outputs |
| Mic input GPIO | `cat /sys/class/gpio/gpio341/value` | `0` (mic selected) |

## Kernel modules

| Test | Command | Expected |
|---|---|---|
| dw_dmac blacklisted | `lsmod \| grep dw_dmac` | No output |
| Shutdown works | `sudo shutdown -h now` | Clean halt, no hang |
| Reboot works | `sudo reboot` | Clean reboot, returns to login |
| i2c-gpio-custom | `lsmod \| grep i2c_gpio` | Module listed |
| spi-gpio-custom | `lsmod \| grep spi_gpio` | Module listed |

## Networking

| Test | Command | Expected |
|---|---|---|
| Ethernet link | `ip link show` then `ping 8.8.8.8` | Link up, ping replies |
| WiFi interface | `ip link show wlan0` or `iw dev` | Interface present |
| WiFi connect | `nmcli dev wifi connect SSID password PASS` | Connected |
| Bluetooth | `bluetoothctl show` | Controller present |

## Hardware sensors (if I2C wired)

| Test | Command | Expected |
|---|---|---|
| I2C bus present | `i2cdetect -l` | Bus(es) listed |
| BNO055 detected | `i2cdetect -y 1` (or correct bus) | Address 0x28 or 0x29 shows |

## System health

| Test | Command | Expected |
|---|---|---|
| CPU temp | `cat /sys/class/thermal/thermal_zone*/temp` | < 80000 (< 80°C) at idle |
| Memory | `free -h` | ~1.8 GB total |
| eMMC health | `mmc extcsd read /dev/mmcblk0 \| grep LIFE` | EXT_CSD_DEVICE_LIFE_TIME < 0x0B |
| DKMS on upgrade | `sudo apt-get install linux-image-amd64 && dkms status` | Modules rebuilt automatically |

## Issues found during testing

*(Add rows here as issues are discovered)*

| Issue | Observed | Root cause | Fix | Build attempt |
|---|---|---|---|---|
| | | | | |
