# PR Tracking SQLite Framework

This repository now includes a lightweight SQLite framework for tracking:

- PR records
- motivations behind changes
- update entries during implementation and validation

## Files

- `tools/pr_tracker.py` — CLI utility for managing tracking data.
- `data/project_updates.db` — SQLite database file generated locally on first `init` (not committed).

## Quick start

```bash
# 1) Initialize database schema
python3 tools/pr_tracker.py init

# 2) Add a motivation
python3 tools/pr_tracker.py add-motivation \
  "Improve release confidence" \
  "Ensure v0.1 is gated on hardware validation evidence."

# 3) Add a PR and attach motivations
python3 tools/pr_tracker.py add-pr \
  "docs: add project state evaluation" \
  --pr-number 12 \
  --branch work \
  --commit-sha abc1234 \
  --state open \
  --motivation-ids 1

# 4) Add an update entry
python3 tools/pr_tracker.py add-update \
  "Added release gate checklist" \
  --pr-id 1 \
  --update-type decision \
  --details "Added explicit pass/fail hardware gates."

# 5) Print report
python3 tools/pr_tracker.py report
```

## Data model

- `motivations`: Why a change exists.
- `pull_requests`: PR metadata and lifecycle state.
- `pr_motivations`: many-to-many link between PRs and motivations.
- `updates`: chronological notes/decisions/tests/status entries, optionally attached to a PR.

## Notes

- Timestamps are UTC ISO-8601.
- `state` and `update_type` are constrained via CHECK clauses.
- Foreign-key constraints are enabled.
