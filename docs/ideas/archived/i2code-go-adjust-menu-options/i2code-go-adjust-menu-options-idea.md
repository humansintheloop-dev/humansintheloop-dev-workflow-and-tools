# Adjust HAS_PLAN Menu Options to Follow Natural Workflow

## Problem

The `i2code go` command's HAS_PLAN menu options are ordered arbitrarily. The default is always "Commit changes" (if uncommitted changes exist) or option 2, regardless of where the user is in the workflow. This forces users to manually select the next logical step rather than just pressing Enter.

## Proposed Solution

Reorder the HAS_PLAN menu options to follow the natural workflow progression and set the default option based on the idea's lifecycle state (from metadata).

### Option Order (stable across all states)

Options appear/disappear based on applicability but always maintain this relative order:

1. Revise the plan
2. Configure/Revise implement options (always visible; label depends on config existence)
3. Move idea to ready/wip (visible when a lifecycle transition is available)
4. Commit changes (visible only when uncommitted changes exist)
5. Implement the entire plan
6. Exit

### Default Logic

The default option advances through the workflow based on lifecycle state:

| Lifecycle State | Condition | Default |
|---|---|---|
| draft | plan exists | Move idea to ready |
| ready | - | Configure/Revise implement options |
| wip | uncommitted changes | Commit changes |
| wip | no uncommitted changes | Implement the entire plan |
| unknown/missing | - | Option 2 (Configure implement options) |

## Scope

- Changes are localized to `src/i2code/go_cmd/orchestrator.py`
- Specifically: `_build_has_plan_options()` (option order) and `_commit_default()` (default logic)
- No changes to menu infrastructure, lifecycle management, or implement config
