# Armbian Build Notes

## How this project relates to Armbian

This repo is an Armbian **userpatches profile** — not a fork, not a board port.
It sits entirely outside the Armbian source tree and is connected via `USERPATCHES_PATH`.

```
~/src/armbian-build/          ← standard Armbian clone, unchanged
~/Claude/Atomic_Pi/           ← this repo (all Atomic Pi-specific work)
  armbian/userpatches/        ← USERPATCHES_PATH points here
    config-atomicpi-*.conf    ← build profiles
    customize-image.sh        ← Armbian's post-build hook
    overlay/                  ← files rsynced into the image root
    extensions/               ← Armbian extension hooks (package injection, etc.)
    packages/                 ← .deb files and reference lists
```

## Build command (any profile)

Always use the wrapper scripts — they handle the symlink setup automatically:

```bash
./scripts/build-minimal.sh
./scripts/build-server.sh
./scripts/build-dev.sh
```

`ARMBIAN_BUILD_DIR` defaults to `$HOME/src/armbian-build`; override to use a different clone.

Do **not** call `./compile.sh build USERPATCHES_PATH=... atomicpi-minimal` directly.
See "USERPATCHES_PATH override" below for why.

## USERPATCHES_PATH override (important)

Armbian's `entrypoint.sh` line 119 does:

```bash
declare -g -r USERPATCHES_PATH="${SRC}"/userpatches
```

This is **read-only and unconditional** — it runs after `apply_cmdline_params_to_env "early"`,
so `USERPATCHES_PATH=...` passed on the command line is applied and then immediately
overridden. The external USERPATCHES_PATH argument does not work.

**Fix:** the build scripts symlink the contents of `armbian/userpatches/` into
`~/src/armbian-build/userpatches/` before calling `compile.sh`. This satisfies:
- Named argument lookup: `atomicpi-minimal` → `userpatches/config-atomicpi-minimal.conf` ✓
- Config `source` calls: `${USERPATCHES_PATH}/config-atomicpi-common.conf` ✓
- `customize-image.sh`, `overlay/`, `extensions/` — all found via symlinks ✓

## Build host requirements

- Ubuntu 22.04 (Jammy) or 24.04 (Noble)
- Run as a normal user — Armbian's `compile.sh` will sudo internally
- ~20 GB free disk space for the build cache
- Internet access (downloads Armbian toolchains and Debian packages)

## Profiles

| Profile | `FIXED_IMAGE_SIZE` | Networking | Headers | Notes |
|---|---|---|---|---|
| atomicpi-minimal | 3500 MB | systemd-networkd | No | Boot/SSH test baseline |
| atomicpi-server | 6000 MB | NetworkManager | No | Daily-use image |
| atomicpi-dev | 9000 MB | NetworkManager | Yes | Kernel/DKMS/GPIO dev |
| atomicpi-desktop | 11000 MB | NetworkManager | No | XFCE; build after headless proven |

All profiles source `config-atomicpi-common.conf`:
- `BOARD=uefi-x86 RELEASE=trixie BRANCH=current`
- `COMPRESS_OUTPUTIMAGE="sha,xz"`
- `ENABLE_EXTENSIONS="atomicpi-profile"`

## How customize-image.sh works

Armbian calls `userpatches/customize-image.sh` inside the image chroot after package installation. At that point:
- `/tmp/overlay/` contains the `userpatches/overlay/` tree
- Packages listed via the `atomicpi-profile` extension are already installed
- The script: rsyncs overlay → sets permissions → enables services → builds DKMS modules

## How the extension works

`extensions/atomicpi-profile.sh` uses Armbian's hook `post_aggregate_packages__atomicpi_add_packages` to inject packages before the build resolves dependencies. This is better than installing in `customize-image.sh` because Armbian handles dependency resolution and deduplication at the right build stage.

## Image output

```
~/src/armbian-build/output/images/
  Armbian_*.img.xz       compressed image
  Armbian_*.img.xz.sha   SHA256 checksum
```

## Kernel branches

| Branch | Description |
|---|---|
| `current` | Stable LTS kernel — use for all published images |
| `edge` | Latest stable kernel — test only |
| `legacy` | Older kernel — not tested for Atomic Pi |
| `cloud` | Stripped cloud/VM kernel — not useful for physical SBC |

## What this project does NOT do

- No Armbian board file (`config/boards/atomic-pi.conf`) — the existing `uefi-x86` board config is sufficient.
- No kernel patches — all needed drivers are mainline.
- No Armbian fork — the Armbian checkout is a standard upstream clone.

If Atomic Pi-specific behavior is discovered that cannot be handled in userpatches, the path is to propose a board config to Armbian upstream, not to fork.
