# Atomic Pi Debian Build — Attempt 1

**Started:** 2026-05-22  
**Host:** pending first run  
**Target:** Intel Atom x5-Z8350 · Debian Trixie (amd64)  
**Goal:** Bootable modern Debian image for Atomic Pi with full hardware support, especially XMOS-driven powered speaker outputs.

---

## Status: Scaffolded v2 — Not Yet Run

All scripts and configuration files written. No build executed yet.

---

## Strategy: Armbian Userpatches Profile (no fork)

This repo is a clean overlay on top of Armbian's upstream `uefi-x86` target.
The Armbian build checkout is never modified. Connection is entirely via `USERPATCHES_PATH`.

```
~/src/armbian-build/     ← standard upstream Armbian clone
~/Claude/Atomic_Pi/      ← this repo
  armbian/userpatches/   ← USERPATCHES_PATH
```

### Pivot history

| Date | Change | Reason |
|---|---|---|
| 2026-05-22 | Custom debootstrap → Armbian uefi-x86 overlay | Armbian already provides uefi-x86/Trixie at Standard tier |
| 2026-05-22 | Monolithic customize-image.sh → overlay + extensions + multi-profile | Cleaner separation; better Armbian idiom |

---

## Architecture

```
./compile.sh build USERPATCHES_PATH=... atomicpi-minimal
  │
  ├─ config-atomicpi-common.conf          BOARD=uefi-x86, RELEASE=trixie, BRANCH=current
  ├─ config-atomicpi-minimal.conf         BUILD_MINIMAL=yes, systemd-networkd, 3500 MB
  │
  ├─ extensions/atomicpi-profile.sh       post_aggregate_packages hook → packages injected
  │
  └─ customize-image.sh                   runs in chroot after packages installed
       ├─ rsync /tmp/overlay/ /           static config files applied
       ├─ systemctl enable (5 services)
       ├─ SSH hardening
       └─ DKMS: i2c-gpio-custom, spi-gpio-custom
```

### Overlay tree (files rsynced into image root)

```
overlay/etc/modprobe.d/blacklist-atomicpi.conf     dw_dmac blacklist
overlay/etc/sysctl.d/99-atomicpi.conf              2 GB RAM tuning
overlay/etc/udev/rules.d/99-atomicpi-gpio.rules    GPIO chip ownership
overlay/etc/asound.conf                            XMOS as ALSA default
overlay/etc/systemd/system/atomicpi-hold-xmos.service
overlay/etc/systemd/system/atomicpi-hold-mic.service
overlay/etc/systemd/system/atomicpi-firstboot.service
overlay/etc/atomicpi/profile                       board identity
overlay/usr/local/sbin/atomicpi-firstboot          validation script
```

---

## Audio Chain (Critical Path)

```
Boot
 └─ atomicpi-hold-xmos.service
      └─ GPIO 349: assert reset (0) → 0.1s → release (1)
           └─ XMOS xCORE enumerates as USB Audio 2.0
                └─ TI TAS5719 class-D amp
                     └─ Powered speaker outputs
                          1.5 W/ch @ 5 V  |  5.0 W/ch @ 12 V

atomicpi-hold-mic.service (Requires: hold-xmos)
 └─ GPIO 341 = 0  → microphone input selected

asound.conf: pcm.!default → hw:XMOS,0
```

---

## Build Profiles

| Profile | Size | Networking | Headers | Status |
|---|---|---|---|---|
| atomicpi-minimal | 3500 MB | systemd-networkd | No | **Build first** |
| atomicpi-server | 6000 MB | NetworkManager | No | Build second |
| atomicpi-dev | 9000 MB | NetworkManager | Yes | After server |
| atomicpi-desktop | 11000 MB | NetworkManager | No | After headless proven |

---

## v0.1 Milestone Criteria

- [ ] Boots from USB
- [ ] Boots from microSD
- [ ] Installs to eMMC
- [ ] Ethernet works
- [ ] WiFi works
- [ ] Bluetooth present
- [ ] HDMI console works
- [ ] XMOS service starts, GPIO 349 released
- [ ] ALSA shows XMOS card
- [ ] Audio plays through powered outputs
- [ ] dw_dmac not loaded
- [ ] Shutdown is clean (no hang)
- [ ] Reboot is clean
- [ ] USB 2/3 devices recognized
- [ ] I2C tools detect BNO055
- [ ] Thermal stays < 80°C at idle
- [ ] DKMS modules survive `apt upgrade`

---

## Open Questions (pre-first-build)

1. **XMOS card name** — `asound.conf` uses `"XMOS"`. Verify with `aplay -l` on first boot.
2. **sysfs GPIO deprecation** — `/sys/class/gpio/` still present in kernel 6.x but deprecated. If it disappears, switch services to `gpioset` (gpiod package).
3. **Armbian headers package name** — verify `linux-headers-current-x86` is correct with `dpkg -l | grep headers` in a running image.
4. **BIOS PXE priority** — CMOS reset may put PXE above eMMC in boot order. Document after first hardware test.
5. **Network in customize-image.sh chroot** — DKMS step git-clones from GitHub; verify Armbian provides network during chroot build.

---

## Stage Run Log

### Stage 1: Armbian base build
*Not yet run.*

### Stage 2: customize-image.sh
*Not yet run.*

### Stage 3: Flash and test
*Not yet run.*

---

## Test Results

*(Populated after first flash — see docs/test-matrix.md)*

---

## Issues Found

*(None yet)*
