# Fix i2code go menu default selection logic

## Problem

The `i2code go` command's menu default option does not follow the natural workflow progression. Two specific issues:

1. When implement options are not yet configured, the default is "Commit changes" instead of "Configure implement options".
2. After configuring options and committing changes, the default is "Revise implement options" instead of "Implement the entire plan".

A root cause is that projects created outside of `i2code go` (e.g., manually or via other commands) have no metadata file, so the lifecycle state is `None` and the lifecycle-aware default logic is bypassed entirely.

## Solution

### 1. Auto-create metadata file

When `i2code go` encounters a project in HAS_PLAN state with no metadata file, auto-create one with `state: draft`. This ensures lifecycle transitions are always available.

### 2. Fix default selection to follow workflow progression

The default menu option should guide the user through the natural workflow:

| State | Condition | Default |
|-------|-----------|---------|
| Draft | (always) | Move to ready |
| Ready | Options not configured | Configure implement options |
| Ready | Options configured | Move to WIP |
| WIP   | Uncommitted changes | Commit changes |
| WIP   | Clean working tree | Implement the entire plan |

## Scope

- `src/i2code/go_cmd/orchestrator.py` — default selection logic in `_lifecycle_default()` and auto-creation of metadata
- Tests in `tests/go-cmd/` — update default selection and lifecycle tests

## Classification

Bug fix in a user-facing feature.
