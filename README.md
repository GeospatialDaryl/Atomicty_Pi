# Atomicty Pi

Modern Debian (Trixie) images for the **Atomic Pi** SBC, built on top of
Armbian's `uefi-x86` target. This repo is an Armbian **userpatches overlay** —
no fork, no kernel patches, no custom board family. All Atomic Pi-specific work
lives here; the Armbian clone stays untouched.

> **Status:** First image built and verified (XFCE desktop, kernel 6.18.32,
> Trixie). Hardware boot testing in progress.

---

## Table of Contents

- [Hardware Overview](#hardware-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Profiles](#build-profiles)
- [Architecture](#architecture)
- [Audio System](#audio-system)
- [Flashing and First Boot](#flashing-and-first-boot)
- [Configuration Reference](#configuration-reference)
- [Known Hardware Quirks](#known-hardware-quirks)
- [Troubleshooting Builds](#troubleshooting-builds)
- [Contributing to Armbian Upstream](#contributing-to-armbian-upstream)
- [Repository Layout](#repository-layout)

---

## Hardware Overview

| Component    | Detail |
|---|---|
| **CPU**      | Intel Atom x5-Z8350, 4-core Cherry Trail, 1.44 GHz (burst 1.92 GHz) |
| **Arch**     | x86-64 only — 32-bit images will not boot |
| **RAM**      | 2 GB LPDDR3 |
| **Storage**  | 16 GB eMMC · `/dev/mmcblk0` |
| **Boot**     | AMI UEFI (AAEON splash) · GPT required · press **Del** or **Tab** to enter BIOS |
| **Ethernet** | Realtek RTL8111G · `r8169` · mainline |
| **WiFi**     | MediaTek RT5572 · `rt2800usb` · USB-attached · needs `firmware-mediatek` |
| **Bluetooth**| Qualcomm CSR8510 · `btusb` · USB-attached |
| **Audio**    | XMOS xCORE USB Audio 2.0 → TI TAS5719 class-D → powered speaker outputs |
| **Serial**   | CN10 · 3.3 V TTL · 115200 8N1 · Pin 1=TX 2=RX 3=GND |
| **IMU**      | Bosch BNO055 (I2C 0x28/0x29) |

> **SD card note:** The SD slot is connected through a Genesys Logic USB
> bridge. It appears as `/dev/sdX`, not `/dev/mmcblk1`.

---

## Prerequisites

**Build host:** Ubuntu 22.04 (Jammy) or 24.04 (Noble). WSL2 is supported.
Do **not** run as root — Armbian calls `sudo` internally for privileged steps.

```bash
# Verify required packages (Armbian installs missing ones automatically)
sudo apt-get install -y git curl wget
```

**Disk space:** ~20 GB free for the build cache (kernel source tree ~2.7 GB on
first run). Subsequent builds reuse the cache and finish in minutes.

**Internet:** Required during the build — Armbian downloads toolchains and
Debian packages. DKMS modules are also cloned from GitHub during the dev
profile build.

---

## Quick Start

```bash
# 1. Clone this repo
git clone https://github.com/GeospatialDaryl/Atomicty_Pi.git
cd Atomicty_Pi

# 2. (Optional) pre-clone Armbian — the build scripts do this automatically
#    but you can speed things up by doing it yourself
git clone --depth=1 https://github.com/armbian/build ~/src/armbian-build

# 3. Build the minimal headless image
./scripts/build-minimal.sh 2>&1 | tee ~/atomicpi-build.log

# 4. Flash to a USB drive (replace /dev/sdX)
sudo ./scripts/flash-usb.sh \
  ~/src/armbian-build/output/images/Armbian-unofficial_*.img \
  /dev/sdX

# 5. Boot the Atomic Pi from USB, then flash to eMMC
sudo ./scripts/flash-emmc.sh /path/to/image.img
```

> **WSL2 users:** The build cannot run in a backgrounded shell because `sudo`
> requires an interactive TTY. Run the build scripts directly in your terminal.

---

## Build Profiles

| Profile | Script | Size | Networking | Kernel Headers | Use case |
|---|---|---|---|---|---|
| `atomicpi-minimal` | `build-minimal.sh` | 3.5 GB | systemd-networkd | No | Boot/SSH baseline |
| `atomicpi-server` | `build-server.sh` | 6 GB | NetworkManager | No | Daily headless use |
| `atomicpi-dev` | `build-dev.sh` | 9 GB | NetworkManager | Yes | Kernel / DKMS / GPIO dev |
| `atomicpi-desktop` | *(interactive menu)* | 11 GB | NetworkManager | No | XFCE desktop |

All profiles share `config-atomicpi-common.conf` (board, release, branch,
extensions) and diverge only in size, networking stack, and headers.

Build the profiles in order: **minimal → server → dev → desktop**.
Confirm hardware boot before building larger profiles.

### Repeat a build with exact options

Armbian prints `Repeat Build Options` at the end of every run. Copy that line
and run it directly from `~/src/armbian-build/` to re-run without the wrapper
script:

```bash
cd ~/src/armbian-build
./compile.sh build BOARD=atomic-pi BRANCH=current BUILD_MINIMAL=yes \
  BUILD_DESKTOP=no KERNEL_CONFIGURE=no RELEASE=trixie
```

---

## Architecture

```
Atomicty_Pi repo
└── armbian/
    ├── atomic-pi.conf              ← Board config (symlinked into Armbian clone)
    └── userpatches/                ← USERPATCHES_PATH (symlinked into Armbian clone)
        ├── config-atomicpi-common.conf
        ├── config-atomicpi-{minimal,server,dev,desktop}.conf
        ├── customize-image.sh      ← Post-build hook (runs in chroot)
        ├── overlay/                ← Files rsynced into image root
        ├── extensions/
        │   ├── atomicpi-profile.sh ← Package injection
        │   └── preset-firstrun.sh  ← First-run wizard presets
        └── packages/
            └── atomicpi-package-list.txt

~/src/armbian-build/    ← Standard upstream Armbian clone (never modified)
    config/boards/
        atomic-pi.conf  ← Symlink → armbian/atomic-pi.conf
    userpatches/        ← Symlinks → armbian/userpatches/*
```

### Why symlinks?

Armbian's `entrypoint.sh:119` unconditionally executes:

```bash
declare -g -r USERPATCHES_PATH="${SRC}/userpatches"
```

This runs *after* command-line arguments are applied, so passing
`USERPATCHES_PATH=...` on the `compile.sh` command line is silently
overridden. The build scripts work around this by symlinking the contents of
`armbian/userpatches/` into `~/src/armbian-build/userpatches/` before calling
`compile.sh`. The board config is handled the same way.

### Build flow

```
./scripts/build-minimal.sh
  │
  ├─ 1. Clone Armbian if absent
  ├─ 2. Symlink userpatches/ and config/boards/atomic-pi.conf
  ├─ 3. Patch logging.sh (💲 → 𓂀 on WSL2)
  └─ 4. ./compile.sh build atomicpi-minimal
         │
         ├─ Kernel build (cached after first run)
         ├─ Rootfs debootstrap + package install
         │   └─ extensions/atomicpi-profile.sh injects packages
         ├─ customize-image.sh (in chroot)
         │   ├─ rsync overlay/ → /
         │   ├─ Enable systemd services
         │   ├─ Harden SSH
         │   └─ Build DKMS modules (dev profile only)
         └─ GRUB install (BIOS + EFI) → .img.xz + .sha
```

### Overlay tree

Files under `armbian/userpatches/overlay/` are rsynced verbatim into the image
root at build time:

```
etc/modprobe.d/blacklist-atomicpi.conf   dw_dmac blacklist (prevents shutdown hang)
etc/sysctl.d/99-atomicpi.conf            RAM tuning (swappiness, dirty ratios)
etc/udev/rules.d/99-atomicpi-gpio.rules  GPIO chip ownership (audio group)
etc/asound.conf                          XMOS as ALSA default device
etc/atomicpi/profile                     Board identity marker
etc/systemd/system/atomicpi-hold-xmos.service
etc/systemd/system/atomicpi-hold-mic.service
etc/systemd/system/atomicpi-firstboot.service
usr/local/sbin/atomicpi-firstboot        First-boot validation script
```

---

## Audio System

The powered speaker outputs are the critical hardware feature of the Atomic Pi.
The full signal path:

```
Power-on
  └─ atomicpi-hold-xmos.service
       └─ GPIO 349: assert 0 (reset) → sleep 100 ms → assert 1 (run)
            └─ XMOS xCORE enumerates as USB Audio 2.0 device
                 └─ I²S → TI TAS5719 class-D amplifier
                      └─ Powered speaker outputs
                           1.5 W/ch @ 5 V input
                           5.0 W/ch @ 12 V input

atomicpi-hold-mic.service (Requires: hold-xmos)
  └─ GPIO 341 = 0  →  microphone input selected (vs. loopback)

/etc/asound.conf
  └─ pcm.!default → hw:XMOS,0
```

### GPIO reference

| sysfs # | gpiochip | Line | Signal | Active state | Notes |
|---|---|---|---|---|---|
| 349 | gpiochip1 | 8 | XMOS_RESET | 1 = running | Released by hold-xmos.service |
| 341 | gpiochip1 | — | AU_MIC_SEL | 0 = mic | Set by hold-mic.service |

> **sysfs deprecation:** `/sys/class/gpio/` is present in kernel 6.x but
> deprecated since ~5.3. If a future kernel removes it, switch the service
> scripts to `gpioset` from the `gpiod` package.

### Verifying audio on first boot

```bash
# Confirm XMOS is running
systemctl status atomicpi-hold-xmos

# List ALSA cards (XMOS should appear)
aplay -l

# Test playback through powered outputs
speaker-test -D hw:XMOS,0 -c 2 -t sine -f 440 -l 1
```

---

## Flashing and First Boot

### Flash to USB / SD card (from workstation)

```bash
# Find your drive
lsblk

# Flash (replace /dev/sdX — this will erase the target)
sudo ./scripts/flash-usb.sh \
  ~/src/armbian-build/output/images/Armbian-unofficial_*.img \
  /dev/sdX
```

Or with `dd` directly:

```bash
sudo dd \
  if=~/src/armbian-build/output/images/Armbian-unofficial_*.img \
  of=/dev/sdX \
  bs=4M status=progress conv=fsync
```

> The image is 3.5–11 GB depending on profile. Your drive must be larger.

### Flash to eMMC (from a running Atomic Pi)

Boot from USB first, then:

```bash
sudo ./scripts/flash-emmc.sh /path/to/Armbian-unofficial_*.img
```

The script checks that you are not currently booted from eMMC before writing.

### Boot order

If the board doesn't boot from your USB drive automatically:

1. Power on and press **Del** immediately at the AAEON splash.
2. Navigate to **Boot → Boot Priority Order**.
3. Move the USB device above PXE/network entries.
4. Save and exit.

After flashing to eMMC, repeat to move eMMC above USB.

### First boot

Armbian automatically:
- Expands the root filesystem to fill the partition
- Regenerates SSH host keys
- Runs the first-run wizard (locale, user, password)

Our `atomicpi-firstboot.service` then runs once to validate:
- XMOS service is active and GPIO 349 = 1
- `dw_dmac` is not loaded
- An Ethernet interface is up

Results are logged to `/var/log/atomicpi-firstboot.log`.

### SSH access

```bash
# Default: password auth is disabled — set your key in the first-run wizard,
# or add it to extensions/preset-firstrun.sh before building.
ssh -i ~/.ssh/your_key user@<board-ip>
```

### Serial console access

```bash
# Connect a 3.3V USB/TTL adapter to CN10 (Pin 1=TX 2=RX 3=GND)
screen /dev/ttyUSB0 115200
# or
minicom -D /dev/ttyUSB0 -b 115200
```

GRUB is configured to mirror output to both VGA and `ttyS0`.

---

## Configuration Reference

### Adding packages to all profiles

Edit `armbian/userpatches/extensions/atomicpi-profile.sh` and add to
`PACKAGE_LIST_ADDITIONAL`:

```bash
function post_aggregate_packages__atomicpi_add_packages() {
    PACKAGE_LIST_ADDITIONAL="${PACKAGE_LIST_ADDITIONAL} your-package"
}
```

### Adding packages to one profile only

Add directly to the profile config:

```bash
# config-atomicpi-server.conf
PACKAGE_LIST_ADDITIONAL="${PACKAGE_LIST_ADDITIONAL} nginx certbot"
```

### Changing build variables

| What to change | File |
|---|---|
| Debian release, kernel branch, compression | `config-atomicpi-common.conf` |
| Image size, networking stack, headers | `config-atomicpi-{profile}.conf` |
| Static config files (ALSA, sysctl, udev) | `overlay/etc/...` |
| Systemd services | `overlay/etc/systemd/system/...` |
| Post-build runtime steps | `customize-image.sh` |
| First-run locale/user/key presets | `extensions/preset-firstrun.sh` |

### Kernel branches

| Branch | Description | Use |
|---|---|---|
| `current` | Stable LTS | All published images |
| `edge` | Latest stable | Testing only |
| `legacy` | Older kernel | Not tested |
| `cloud` | Stripped VM kernel | Not useful on physical hardware |

### Image output

```
~/src/armbian-build/output/images/
  Armbian-unofficial_<ver>_Atomic-pi_trixie_current_<kernel>_<profile>.img
  Armbian-unofficial_<ver>_Atomic-pi_trixie_current_<kernel>_<profile>.img.sha
  Armbian-unofficial_<ver>_Atomic-pi_trixie_current_<kernel>_<profile>.img.txt
```

---

## Known Hardware Quirks

| Quirk | Root cause | Fix |
|---|---|---|
| **Hangs on shutdown/reboot** | `dw_dmac` conflicts with Z8350 HSUART DMA controller | `blacklist-atomicpi.conf` blacklists `dw_dmac` and `dw_dmac_core` — **mandatory** |
| **XMOS silent at boot** | XMOS xCORE starts in hardware reset | `atomicpi-hold-xmos.service` deasserts GPIO 349 |
| **SD card not `/dev/mmcblk1`** | Genesys Logic SD bridge is USB-attached | SD appears as `/dev/sdX`; don't rely on mmcblk numbering |
| **USB instability** | Board draws more current than an unpowered port can supply | Use a powered hub during installation |
| **CMOS reset button** | Located near board edge, easily pressed accidentally | Corrupts eMMC boot partitions; handle carefully |
| **Default boot order** | CMOS reset may put PXE above eMMC | Re-order in BIOS after first eMMC flash |

---

## Troubleshooting Builds

### `Unknown argument [atomicpi-minimal]`

The build scripts must be used (`./scripts/build-minimal.sh`), not
`compile.sh` with `USERPATCHES_PATH=...` on the command line. Armbian
overrides `USERPATCHES_PATH` unconditionally in `entrypoint.sh:119`.
The wrapper scripts install symlinks to work around this.

### `sudo: a terminal is required to read the password`

Running the build in a backgrounded or non-interactive shell fails because
`sudo` needs a TTY. Run the build scripts directly in your terminal.

### `RELEASE: unbound variable` in customize-image.sh

Armbian passes `RELEASE`, `BOARD`, etc. as **positional arguments** to
`customize-image.sh`, not environment variables. The script unpacks them as
`RELEASE=${1:-}` at the top. If you see this error, the old version of the
script is being used — re-run the build scripts to re-symlink.

### DKMS modules fail to build

DKMS requires kernel headers. Only the **dev profile** has
`INSTALL_HEADERS=yes`. On all other profiles, the DKMS step is skipped with
a message: `>>> [5] DKMS skipped — kernel headers not installed`.

If the modules are needed outside the dev profile, switch to the dev profile
or install `linux-headers-current-x86` manually after first boot.

### Build stalls at kernel download (~2.7 GB)

On first run, Armbian downloads the full kernel git tree. This is a one-time
cost. Accept the prompt (or pass `KERNEL_GIT=full` to skip the countdown).
Subsequent builds use the cached tree.

### Smoke-testing without hardware

```bash
./scripts/qemu-smoke-test.sh \
  ~/src/armbian-build/output/images/Armbian-unofficial_*.img
```

Requires `qemu-system-x86_64`, `ovmf`, and `expect`. Boots the image in
QEMU/OVMF and checks for a login prompt within 180 seconds.

---

## Contributing to Armbian Upstream

This project is structured so that the board config can be submitted to
Armbian as a Community Supported board (`atomic-pi.csc`).

**Scope of the upstream PR:** only `config/boards/atomic-pi.csc`.
Everything else (audio services, DKMS modules, ALSA config) stays in this
userpatches repo — it is Atomic Pi-specific, not Armbian's responsibility.

**Before opening the PR:**

1. Confirm a successful hardware boot.
2. Run `armbianmonitor -u` on the booted board and save the URL.
3. Capture the serial console boot log (see `docs/hardware-boot-evidence.md`).
4. Fill in the test matrix (see `docs/test-matrix.md`).

The upstream board config file will declare `BOARD_VENDOR`, `BOARDFAMILY`,
`KERNEL_TARGET`, `SERIALCON`, and CSC-tier CLI/desktop targets. See
`armbian/atomic-pi.conf` for the current draft.

A full PR description template is at `docs/armbian-pr.md` (pending hardware
confirmation).

---

## Repository Layout

```
armbian/
  atomic-pi.conf                     Board config → symlinked into Armbian clone
  userpatches/
    config-atomicpi-common.conf       Shared base (board, release, branch, extensions)
    config-atomicpi-minimal.conf      3.5 GB · systemd-networkd · no headers
    config-atomicpi-server.conf       6 GB   · NetworkManager  · no headers
    config-atomicpi-dev.conf          9 GB   · NetworkManager  · kernel headers
    config-atomicpi-desktop.conf      11 GB  · NetworkManager  · XFCE
    customize-image.sh                Post-build hook (overlay → services → DKMS)
    extensions/
      atomicpi-profile.sh             Package injection via Armbian hook
      preset-firstrun.sh              First-run wizard presets
    overlay/                          Files rsynced verbatim into image root
      etc/modprobe.d/                 dw_dmac blacklist
      etc/sysctl.d/                   RAM tuning
      etc/udev/rules.d/               GPIO chip ownership
      etc/asound.conf                 XMOS as default ALSA device
      etc/atomicpi/profile            Board identity marker
      etc/systemd/system/             XMOS, mic, and firstboot services
      usr/local/sbin/                 atomicpi-firstboot validation script
    packages/
      atomicpi-package-list.txt       Reference package list

scripts/
  build-minimal.sh                   Build minimal profile
  build-server.sh                    Build server profile
  build-dev.sh                       Build dev profile
  flash-usb.sh                       Write image to USB/SD (workstation)
  flash-emmc.sh                      Write image to eMMC (on the board)
  firstboot.sh                       Interactive hardware verification
  mount-image.sh                     Loopback-mount image for inspection
  qemu-smoke-test.sh                 Boot image in QEMU/OVMF

docs/
  atomic-pi-hardware.md              Full hardware reference
  boot-uefi.md                       UEFI/BIOS, serial console, boot order
  emmc-install.md                    Partition layout and flash procedure
  test-matrix.md                     Hardware validation checklist
  armbian-build-notes.md             Build system internals and decisions
  hardware-boot-evidence.md          Commands and artifacts for Armbian PR

.github/workflows/
  build-armbian.yml                  CI: workflow_dispatch, 3 profiles

BuildAttempt_1.json                  Machine-readable build log
BuildAttempt_1.md                    Human-readable build log
```

---

## License

GPL-3.0. See [LICENSE](LICENSE).
