# Specification: Adjust HAS_PLAN Menu Options to Follow Natural Workflow

## Purpose and Background

The `i2code go` command drives an interactive workflow loop. When the orchestrator detects `WorkflowState.HAS_PLAN`, it presents a menu of actions. Currently, the menu options are ordered arbitrarily and the default selection does not reflect where the user is in the lifecycle. This forces users to manually scan and select the correct next step instead of pressing Enter.

This feature reorders the HAS_PLAN menu and introduces lifecycle-aware default selection so the menu guides users through the natural progression: draft → ready → configure → wip → commit → implement.

## Target Users

Solo developer using `i2code go` to drive idea-to-implementation workflows.

## Problem Statement

1. **Option order is inconsistent** — The current `_build_has_plan_options()` produces: `[Revise plan, Configure/Revise implement, Move?, Commit?, Implement, Exit]`. While this order happens to match the desired order, the default selection logic does not guide the user through the workflow.

2. **Default selection is not context-aware** — `_commit_default()` returns the index of "Commit changes" if uncommitted changes exist, otherwise falls back to option 2. It ignores the lifecycle state entirely. A user in `draft` state with no uncommitted changes gets "Configure implement options" as the default, when the logical next step is "Move idea to ready".

## Goals

- The default menu selection reflects the next logical workflow step based on lifecycle state.
- Users can complete the full draft → ready → configure → wip → implement flow by pressing Enter at each menu presentation.
- The option order remains stable across all lifecycle states (options appear/disappear but never reorder).

## In Scope

- Replacing `_commit_default()` with lifecycle-aware default logic.
- Ensuring `_build_has_plan_options()` maintains the stable option order documented below.
- Updating existing tests for the changed default behavior.

## Out of Scope

- Changes to the menu infrastructure (`get_user_choice`, `MenuConfig`).
- Changes to lifecycle state management (`execute_transition`, `read_metadata`).
- Changes to implement config handling.
- Changes to menus for other `WorkflowState` values (`NO_IDEA`, `HAS_IDEA_NO_SPEC`, `HAS_SPEC`).

## Functional Requirements

### FR-1: Stable Option Order

`_build_has_plan_options()` must produce options in this fixed relative order. Options that are conditionally present appear in their designated position or are omitted entirely:

| Position | Option Label | Visibility |
|---|---|---|
| 1 | `"Revise the plan"` | Always |
| 2 | `"Configure implement options"` / `"Revise implement options"` | Always (label depends on config file existence) |
| 3 | `"Move idea to ready"` / `"Move idea to wip"` | Only when a lifecycle transition is available |
| 4 | `"Commit changes"` | Only when uncommitted changes exist |
| 5 | `"Implement the entire plan"` (with config suffix from `build_implement_label`) | Always |
| 6 | `"Exit"` | Always |

### FR-2: Lifecycle-Aware Default Selection

The default option is determined by reading the idea's lifecycle state from metadata and evaluating conditions:

| Lifecycle State | Condition | Default Option |
|---|---|---|
| `draft` | — | `"Move idea to ready"` |
| `ready` | — | `"Configure implement options"` or `"Revise implement options"` |
| `wip` | Uncommitted changes exist | `"Commit changes"` |
| `wip` | No uncommitted changes | `"Implement the entire plan"` |
| No metadata / unknown state | — | Option at position 2 (Configure/Revise implement options) |

The default is expressed as a 1-based index into the options list returned by `_build_has_plan_options()`.

### FR-3: Metadata Reading for Default Logic

The default logic must read the lifecycle state from `self._project.metadata_file` using `read_metadata()`. The existing `_lifecycle_move_label()` method already reads metadata and can serve as a reference, but the default logic needs the raw state string (e.g., `"draft"`, `"ready"`, `"wip"`), not just the move label.

## Security Requirements

Not applicable — this is a local CLI menu presentation change with no network operations, authentication, or authorization.

## Non-Functional Requirements

### UX

- The menu must render identically to the current menu (same prompt format, same visual structure). Only the default marker position changes.
- Users who have memorized option numbers may need to adjust. The option order itself is unchanged from the current implementation, so this impact is limited to the default indicator.

### Performance

- No additional file I/O beyond what already exists. The metadata file is already read by `_lifecycle_move_label()`. The default logic should reuse the same metadata read rather than reading the file twice.

### Testability

- Default selection logic must be testable without file system access (metadata state injectable via `OrchestratorDeps` or test fixtures).

## Success Metrics

- In each lifecycle state, pressing Enter (accepting the default) advances the workflow to the next logical step.
- No regressions in existing menu behavior for non-default selections.

## Epics and User Stories

### Epic: Lifecycle-Aware Menu Defaults

**US-1**: As a developer in `draft` state with a completed plan, I want the default menu option to be "Move idea to ready" so I can advance the lifecycle by pressing Enter.

**US-2**: As a developer in `ready` state, I want the default menu option to be "Configure implement options" (or "Revise implement options" if already configured) so I can set up implementation before moving to `wip`.

**US-3**: As a developer in `wip` state with uncommitted changes, I want the default menu option to be "Commit changes" so I can commit my work before implementing the next task.

**US-4**: As a developer in `wip` state with no uncommitted changes, I want the default menu option to be "Implement the entire plan" so I can start/continue implementation by pressing Enter.

**US-5**: As a developer with missing or unrecognized metadata state, I want the default to fall back to option 2 (Configure/Revise implement options) so the menu remains usable.

## User-Facing Scenarios

### Scenario 1 (Primary): Full Workflow Progression via Defaults

Starting from `draft` state with a plan file:

1. Menu shows with "Move idea to ready" as default → user presses Enter → idea moves to `ready`.
2. Menu shows with "Configure implement options" as default → user presses Enter → configures implementation.
3. Menu shows with "Move idea to wip" as default → user presses Enter → idea moves to `wip`.
4. Menu shows with "Implement the entire plan" as default → user presses Enter → implementation runs.
5. After implementation creates changes, menu shows with "Commit changes" as default → user presses Enter → changes committed.
6. Menu shows with "Implement the entire plan" as default → user presses Enter → next task implemented.

### Scenario 2: Non-Default Selection

In any lifecycle state, the user selects a non-default option (e.g., "Revise the plan" while in `wip` state). The selected action executes normally. The menu re-displays with the default recalculated based on current state.

### Scenario 3: Missing Metadata

An idea directory has a plan file but no metadata file. The menu shows with option 2 (Configure/Revise implement options) as default. All options function normally.

### Scenario 4: Uncommitted Changes in Draft State

An idea is in `draft` state and has uncommitted changes. The default is still "Move idea to ready" (lifecycle state takes precedence). "Commit changes" is visible in the menu but is not the default.
