# Specification: Fix i2code go menu default selection logic

## Purpose and background

The `i2code go` command provides an interactive menu that guides users through the idea-to-implementation workflow: drafting, readying, configuring, committing, and implementing. The menu highlights a `[default]` option so the user can press Enter to take the natural next step.

Currently, the default selection logic has two problems:

1. **Missing metadata file** — When idea/spec/plan files are created outside `i2code go` (e.g., manually or via `i2code idea`/`i2code spec`/`i2code plan`), no metadata file exists. Without metadata, lifecycle move options ("Move idea to ready/wip") don't appear, and the fallback default logic picks the wrong option.

2. **Incorrect defaults in ready state** — When the implement config file already exists, the ready-state default remains "Revise implement options" instead of advancing to "Move idea to wip".

## Target users

Developers using `i2code go` to manage idea lifecycle and implementation workflow.

## Problem statement and goals

**Problem:** The default menu option does not follow the natural workflow progression, forcing users to manually select the correct next step instead of pressing Enter.

**Goals:**
- The default option always reflects the logical next step in the workflow
- Projects created outside `i2code go` participate in the lifecycle without manual setup
- Users can progress through the entire workflow (draft → ready → wip → implement) by repeatedly pressing Enter at each menu

## In-scope

- Auto-creation of metadata file with `state: draft` when `i2code go` detects HAS_PLAN state with no metadata
- Fixing `_lifecycle_default()` in `orchestrator.py` to follow the correct progression
- Updating existing tests and adding new tests for the fixed behavior

## Out-of-scope

- Changes to lifecycle transition rules in `transition_rules.py`
- Changes to the menu option labels or ordering
- Changes to the implement config prompting flow
- Auto-creation of metadata in states other than HAS_PLAN (NO_IDEA, HAS_IDEA_NO_SPEC, HAS_SPEC)

## Functional requirements

### FR-1: Auto-create metadata for projects without one

When `_read_lifecycle_state()` in `orchestrator.py:298` finds no metadata file and the workflow state is HAS_PLAN, it must:

1. Create a metadata file at `{project.metadata_file}` with content `state: draft` using the existing `write_metadata()` function from `i2code.idea.metadata`
2. Return `"draft"` as the lifecycle state

This ensures the menu always includes lifecycle move options when a plan exists.

### FR-2: Default selection follows workflow progression

The `_lifecycle_default()` method (`orchestrator.py:332`) must select defaults according to this table:

| Lifecycle state | Condition | Default option |
|----------------|-----------|----------------|
| `"draft"` | (always) | `MOVE_TO_READY` ("Move idea to ready") |
| `"ready"` | Config file does not exist | `CONFIGURE_IMPLEMENT` ("Configure implement options") |
| `"ready"` | Config file exists | `MOVE_TO_WIP` ("Move idea to wip") |
| `"wip"` | Uncommitted changes in project dir | `COMMIT_CHANGES` ("Commit changes") |
| `"wip"` | Clean working tree | Implement option (starts with `IMPLEMENT_PLAN`) |

The current fallback path (lines 342-344) for unknown/missing state becomes unreachable after FR-1 is implemented for HAS_PLAN, but should remain as a defensive fallback using the same configure → commit → implement priority.

### FR-3: No change to menu option ordering or labels

The `_build_has_plan_options()` method remains unchanged. Only the default selection index changes.

## Security requirements

Not applicable — this is a local CLI tool with no authentication, authorization, or network operations.

## Non-functional requirements

- **UX:** Pressing Enter at each menu step should advance the user through the full workflow without requiring manual option selection
- **Backward compatibility:** Projects that already have metadata files are unaffected — the auto-create only fires when no metadata file exists
- **Idempotency:** Running `i2code go` multiple times on the same project does not overwrite an existing metadata file

## Success metrics

- All five workflow progression scenarios (draft, ready-no-config, ready-with-config, wip-dirty, wip-clean) select the correct default
- Projects created outside `i2code go` show lifecycle move options on first run

## Epics and user stories

### Epic: Correct default workflow progression

**US-1:** As a developer, when I run `i2code go` on a project created outside the tool, I see lifecycle move options (Move to ready/wip) so I can manage the idea lifecycle.

**US-2:** As a developer in draft state, the default is "Move to ready" so I can advance by pressing Enter.

**US-3:** As a developer in ready state who hasn't configured implement options, the default is "Configure implement options" so I set up before implementing.

**US-4:** As a developer in ready state who has already configured implement options, the default is "Move to wip" so I can advance to implementation.

**US-5:** As a developer in wip state with uncommitted changes, the default is "Commit changes" so I save my work first.

**US-6:** As a developer in wip state with a clean tree, the default is "Implement the entire plan" so I can start implementation by pressing Enter.

## Scenarios

### Primary scenario: Full workflow progression on externally-created project

A developer creates idea, spec, and plan files manually (not via `i2code go`). They then run `i2code go` repeatedly, pressing Enter each time:

1. First run — no metadata exists. Auto-created with `state: draft`. Menu shows "Move idea to ready" as default. User presses Enter → state moves to draft→ready.
2. Second run — state is ready, no config file. Menu shows "Configure implement options" as default. User presses Enter → configures options.
3. Third run — state is ready, config exists. Menu shows "Move idea to wip" as default. User presses Enter → state moves to ready→wip.
4. Fourth run — state is wip, uncommitted changes from state transition. Menu shows "Commit changes" as default. User presses Enter → changes committed.
5. Fifth run — state is wip, clean tree. Menu shows "Implement the entire plan: i2code implement [flags]" as default. User presses Enter → implementation begins.

### Scenario: Project already has metadata

A developer who created the project via `i2code go` (metadata already exists with `state: ready`). Running `i2code go` does not overwrite the metadata. Defaults follow the ready-state logic.

### Scenario: Unknown lifecycle state

A project with metadata containing an unrecognized state (e.g., `state: archived`). The fallback default logic applies: configure → commit → implement priority.

## Test expectations

### Tests to update

- `test_orchestrator_lifecycle_menu.py::TestReadyIdeaMenu::test_ready_idea_with_config_defaults_to_revise` — Change expected default from `REVISE_IMPLEMENT` to `MOVE_TO_WIP`
- `test_orchestrator_default_selection.py::TestDefaultSelectionByConfig::test_config_exists_no_changes_defaults_to_revise` — Change expected default from `REVISE_IMPLEMENT` to `CONFIGURE_IMPLEMENT` (this test uses a `wip/` directory path so no metadata auto-create, but the fallback should now prefer configure)

### Tests to add

- Auto-creation of metadata file when none exists in HAS_PLAN state
- Verify metadata is not overwritten when it already exists
- Ready state with config file defaults to `MOVE_TO_WIP`
- Full progression scenario (optional integration-level test)
