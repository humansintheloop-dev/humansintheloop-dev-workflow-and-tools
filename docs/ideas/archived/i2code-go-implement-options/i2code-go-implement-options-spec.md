# Specification: i2code go Implementation Options Configuration

## Purpose and Background

The `i2code go` command orchestrates the idea-to-code workflow through an interactive menu system. When a plan exists (HAS_PLAN state), the user needs to configure how implementation will run before committing and launching `i2code implement`. Currently, the "Configure implement options" menu item only appears after a config file already exists, making it easy to miss entirely. The configuration also lacks support for isolation type, which is already available as a CLI argument but not exposed in the menu-driven config flow.

This feature restores and improves the implementation options configuration UX by making it always visible in the HAS_PLAN menu and adding isolation type as a third configurable option.

## Target Users

- Developers using `i2code go` to manage the idea-to-implementation workflow.

## Problem Statement

1. **Discoverability**: The "Configure implement options" menu item is hidden until the config file exists. Users may never see it and run implementations with default settings without realizing they can customize them.
2. **Missing isolation option**: The `--isolation-type` CLI flag (none, nono, container, vm) exists in `i2code implement` but cannot be set through the `i2code go` menu config flow.
3. **Menu ordering**: The current menu places "Commit changes" before "Configure", but users should configure before committing.

## Goals

1. Always show the "Configure/Revise implementation options" menu item in the HAS_PLAN state.
2. Add `isolation_type` to the config prompt flow and config file format.
3. Restructure the HAS_PLAN menu ordering so configuration comes before committing.
4. Make the default menu selection guide users toward configuring before committing.

## In-Scope

- Modify `_build_has_plan_options()` in `orchestrator.py` to always include the configure option and reorder menu items.
- Modify `_commit_default()` to return the configure option as default when no config exists.
- Add `isolation_type` field to the config prompt flow in `implement_config.py`.
- Update `read_implement_config()`, `write_implement_config()`, `prompt_implement_config()`, `build_implement_flags()`, and `build_implement_label()` to handle the new field.
- Add backward compatibility: treat missing `isolation_type` as `"none"` on read.
- Update `_display_implement_config()` to show isolation type.

## Out-of-Scope

- Adding new isolation backends (nono, container, vm already exist).
- Changes to `i2code implement` CLI arguments (they already support `--isolation-type` and `--isolate`).
- Changes to any workflow state other than HAS_PLAN.
- Migrating existing config files on disk (auto-migrate on read is sufficient).

## Functional Requirements

### FR1: Menu Structure in HAS_PLAN State

The HAS_PLAN menu items appear in this fixed order. Conditional items are omitted when not applicable, but the relative order is preserved.

| Position | Label | Condition |
|----------|-------|-----------|
| 1 | Revise the plan | Always |
| 2 | Configure implementation options | Config file does NOT exist |
| 2 | Revise implementation options | Config file exists |
| 3 | Move idea to ready / Move idea to wip | Idea is in draft / ready state |
| 4 | Commit changes | Uncommitted changes in idea directory |
| 5 | Implement the entire plan: i2code implement {flags} | Always |
| 6 | Exit | Always |

The configure/revise label at position 2 uses the existing `CONFIGURE_IMPLEMENT` constant (`"Configure implement options"`) when no config file exists. When the config file exists, the label changes to `"Revise implement options"`.

### FR2: Default Menu Selection

| Condition | Default |
|-----------|---------|
| No config file exists | Position 2 (Configure implementation options) |
| Config exists and uncommitted changes | Position of "Commit changes" |
| Config exists and no uncommitted changes | Position 2 (Revise implementation options) |

### FR3: Config Prompt Flow

`prompt_implement_config(menu_fn)` asks three questions in order:

**Question 1: Mode**
```
How should Claude run?
  1) Interactive [default]
  2) Non-interactive
```

**Question 2: Isolation type**
```
Isolation type?
  1) None [default]
  2) Nono
  3) Container
  4) VM
```

**Question 3: Branch strategy** (only if isolation type is "none")
```
Where should implementation happen?
  1) Worktree (branch + PR) [default]
  2) Trunk (current branch, no PR)
```

If isolation type is not "none", trunk is automatically set to `false` (worktree is implied by isolation).

Return value changes from `(interactive, trunk)` to `(interactive, isolation_type, trunk)`.

### FR4: Config File Format

File: `{name}-implement-config.yaml`

```yaml
interactive: true
isolation_type: none
trunk: false
```

All three fields are always written, regardless of which questions were asked. The `isolation_type` field stores the string value: `none`, `nono`, `container`, or `vm`.

### FR5: Config Read with Backward Compatibility

`read_implement_config(path)` returns a dict with three keys: `interactive` (bool), `isolation_type` (str), `trunk` (bool). If `isolation_type` is missing from the file, it defaults to `"none"`.

### FR6: Build Implement Flags

`build_implement_flags(config)` produces CLI flags from the config dict:

| Config | Flag |
|--------|------|
| `interactive: false` | `--non-interactive` |
| `trunk: true` | `--trunk` |
| `isolation_type` != `"none"` | `--isolation-type {value}` |

When `isolation_type` is not `"none"`, the `--isolate` flag is NOT explicitly added because `ImplementCommand` already auto-enables it when `--isolation-type` is provided.

### FR7: Build Implement Label

`build_implement_label(config_path)` builds the menu label showing the exact command. Examples:

- No config: `"Implement the entire plan: i2code implement"`
- Interactive + worktree: `"Implement the entire plan: i2code implement"`
- Non-interactive + nono: `"Implement the entire plan: i2code implement --non-interactive --isolation-type nono"`
- Interactive + trunk: `"Implement the entire plan: i2code implement --trunk"`

### FR8: Display Config

`_display_implement_config(config)` prints all three settings:

```
Implementation options:
  Mode: interactive
  Branch: worktree
  Isolation: none
```

### FR9: Configure and Revise

Both `_ensure_implement_config()` and `_configure_implement()` are updated to pass and receive the three-field tuple `(interactive, isolation_type, trunk)` and call the updated `write_implement_config(path, interactive, isolation_type, trunk)`.

## Non-Functional Requirements

- **Backward compatibility**: Existing config files with only `interactive` and `trunk` fields continue to work without user intervention.
- **Testability**: All functions in `implement_config.py` remain pure or accept injected dependencies (menu_fn). The orchestrator continues to use `OrchestratorDeps` for test injection.

## Success Metrics

- The "Configure/Revise implementation options" menu item appears in every HAS_PLAN menu interaction.
- Users can set isolation type through the menu without manually editing YAML or passing CLI flags.
- Existing config files are read without error or re-prompting.

## Epics and User Stories

### Epic 1: Menu Restructuring

**US1.1**: As a user in HAS_PLAN state with no config file, I see "Configure implementation options" as option 2 and it is the default selection, so I am guided to configure before committing.

**US1.2**: As a user in HAS_PLAN state with an existing config file, I see "Revise implementation options" as option 2, and "Commit changes" is the default selection (if uncommitted changes exist).

**US1.3**: As a user in HAS_PLAN state, I see the "Implement" menu label showing the exact flags that will be used based on my config.

### Epic 2: Isolation Type in Config Flow

**US2.1**: As a user configuring implementation options, I am asked for isolation type after choosing interactive/non-interactive mode, and I can choose from None, Nono, Container, or VM.

**US2.2**: As a user who selects an isolation type other than "none", I am NOT asked about trunk/worktree because worktree is implied.

**US2.3**: As a user who selects isolation type "none", I am asked about trunk vs worktree as the third question.

### Epic 3: Config File and Backward Compatibility

**US3.1**: As a user with an existing config file from before this change (missing `isolation_type`), the system reads my file and treats isolation as "none" without prompting me again.

**US3.2**: As a user who configures or revises options, the saved config file always contains all three fields (`interactive`, `isolation_type`, `trunk`).

## Primary End-to-End Scenario

**Scenario: First-time configuration and implementation**

1. User runs `i2code go my-idea` with a plan already created but no implement config file.
2. The HAS_PLAN menu displays with "Configure implementation options" as option 2 and the default.
3. User presses Enter (accepts default).
4. System asks "How should Claude run?" — user selects "Non-interactive".
5. System asks "Isolation type?" — user selects "Nono".
6. System skips the trunk/worktree question (nono implies worktree).
7. System writes `my-idea-implement-config.yaml` with `interactive: false`, `isolation_type: nono`, `trunk: false`.
8. Menu redisplays with "Revise implementation options" at position 2, "Commit changes" as default, and "Implement the entire plan: i2code implement --non-interactive --isolation-type nono" showing the configured flags.
9. User selects "Commit changes", then selects "Implement".
10. System runs `i2code implement --non-interactive --isolation-type nono my-idea-dir`.

**Scenario: Revising existing configuration**

1. User has an existing config file. Menu shows "Revise implementation options" at position 2.
2. User selects "Revise implementation options".
3. System re-prompts all three questions. User changes isolation from "nono" to "none" and branch strategy to "trunk".
4. System overwrites config file with `interactive: false`, `isolation_type: none`, `trunk: true`.
5. Menu redisplays with "Implement the entire plan: i2code implement --non-interactive --trunk".

**Scenario: Backward-compatible config read**

1. User has a config file from before this change containing only `interactive: true` and `trunk: false`.
2. System reads the file, defaults `isolation_type` to `"none"`.
3. Menu displays "Implement the entire plan: i2code implement" (no extra flags since all are defaults).
4. User can revise options to set isolation type if desired.
