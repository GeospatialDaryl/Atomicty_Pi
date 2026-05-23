# Image Layout

## Disk layout (produced by Armbian uefi-x86)

```
┌──────────────────────────────────────────────────────┐
│  GPT partition table                                  │
├──────────────┬────────────────────────────────────────┤
│  Partition 1 │ EFI System Partition (ESP)             │
│              │ Size:   ~256 MB                        │
│              │ Format: FAT32                          │
│              │ Mount:  /boot/efi                      │
│              │ Content: GRUB EFI binary, kernels      │
├──────────────┼────────────────────────────────────────┤
│  Partition 2 │ Linux root                             │
│              │ Size:   remainder                      │
│              │ Format: ext4                           │
│              │ Mount:  /                              │
│              │ Auto-expands on first boot (Armbian)   │
└──────────────┴────────────────────────────────────────┘
```

## eMMC target

The image writes to `/dev/mmcblk0` (the 16 GB eMMC):

```
/dev/mmcblk0p1   /boot/efi    vfat    256 MB
/dev/mmcblk0p2   /            ext4    ~15.7 GB (after expansion)
```

## Bootloader

- **GRUB EFI** (`grub-efi-amd64`)
- EFI binary at `/boot/efi/EFI/BOOT/BOOTX64.EFI` (removable/fallback path)
- Also registered as `atomicpi` in the EFI boot manager
- GRUB config: `/boot/grub/grub.cfg`
- Serial console: 115200 baud on `ttyS0` (mirrored to VGA)
- Boot timeout: 3 seconds

## Build output location

Armbian places finished images in:
```
armbian-build/output/images/
  Armbian_*.img.xz        compressed image
  Armbian_*.img.xz.sha    SHA256 checksum
```

## Flash procedure

```
# 1. On workstation: write image to USB drive
sudo ./scripts/flash-usb.sh armbian-build/output/images/Armbian_*.img.xz /dev/sdX

# 2. Boot Atomic Pi from USB drive

# 3. On Atomic Pi: write image to internal eMMC
sudo ./scripts/flash-emmc.sh /media/usb/Armbian_*.img.xz
# or if image is on the same USB drive:
sudo ./scripts/flash-emmc.sh /dev/sda  # (dd directly from device)
```
