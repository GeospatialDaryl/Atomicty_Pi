# Project State Evaluation (2026-05-23)

## Executive Summary

The project is in a **solid early-build state**: image construction is working, architecture choices are coherent, and key known build-time issues have been resolved. The biggest remaining gap is that **hardware validation is largely incomplete** relative to the stated v0.1 milestone.

Current maturity estimate:
- **Build pipeline maturity:** 7/10
- **Hardware validation maturity:** 2/10
- **Release readiness (v0.1):** 3/10

## What is Working Well

1. **Correct strategic architecture**
   - Uses Armbian as upstream and keeps Atomic Pi specifics in userpatches.
   - Avoids unnecessary board-framework forking.

2. **Build reproducibility is improving**
   - Clear profile split: minimal/server/dev/desktop.
   - Wrapper scripts and config layering are present and understandable.

3. **Critical build blockers already resolved**
   - USERPATCHES path handling workaround implemented.
   - `customize-image.sh` argument handling corrected.
   - DKMS path guarded for non-dev profiles.

4. **Hardware-specific boot/audio handling is encoded**
   - XMOS/mic systemd services included.
   - `dw_dmac` blacklist and sysctl/udev/audio overlays are in place.

## Current Risks / Gaps

1. **Milestone evidence mismatch**
   - Repository status claims a successful desktop image build, but v0.1 criteria are still mostly unchecked.
   - Stage 3 (flash-and-test) has not been run according to the build logs.

2. **Validation order drift**
   - Documented profile order recommends minimal → server → dev → desktop.
   - First successful image appears to be desktop, which is useful but does not substitute for headless baseline proof.

3. **Hardware confidence remains low**
   - No logged pass/fail evidence yet for USB boot, eMMC install, shutdown/reboot stability, XMOS playback, WiFi/Bluetooth, and BNO055 checks.

4. **Potential maintainability issue**
   - Symlink workaround into `~/src/armbian-build` is practical but fragile if host paths vary; this should be treated as a controlled dependency and tested on a second host.

## Suggested Priority Plan (Next 1-2 Days)

1. **Run minimal profile build and test loop first**
   - Build: `./scripts/build-minimal.sh`
   - Validate: USB boot, SSH, network, clean reboot/shutdown, eMMC flash path.

2. **Convert test-matrix into logged pass/fail evidence**
   - Fill `docs/test-matrix.md` entries with date/time and exact command outputs.
   - Update `BuildAttempt_1.json/.md` after each verification block.

3. **Confirm audio critical path explicitly**
   - Validate XMOS enumeration (`aplay -l`) and powered speaker playback.
   - Record GPIO service behavior and failure modes if any.

4. **Then progress server/dev profiles**
   - Server: network manager + podman behavior.
   - Dev: kernel headers + DKMS persistence across reboot and after upgrade.

5. **Only then claim v0.1 milestone**
   - Gate v0.1 on completed matrix, not on build success alone.

## Release Readiness Gate Recommendation

Before declaring v0.1 complete, require all of the following to be true:
- Minimal image boots and survives reboot/shutdown on real hardware.
- eMMC install path validated end-to-end.
- XMOS audio output verified audibly.
- Network stack verified (Ethernet + WiFi).
- `BuildAttempt_1.json` and `BuildAttempt_1.md` fully updated with timestamps and outcomes.

## Bottom Line

This is a **promising and well-structured project** that has moved past initial build-system uncertainty. The immediate need is not more architecture work; it is **disciplined hardware verification and evidence logging** to convert a successful build into a trustworthy release.
