# i2code go invoking implement - Specification

## Purpose and Background

`i2code go` is the orchestrator that drives the idea-to-code workflow. When a plan is ready, the user selects "Implement the entire plan" from the menu, and `i2code go` invokes `i2code implement "$dir"` with no options. This means every implementation run uses the default mode (worktree + interactive), with no way to choose trunk mode or non-interactive execution without bypassing `i2code go` entirely.

This feature adds the ability for `i2code go` to prompt the user for key implementation options, persist them in a YAML config file, and pass them to `i2code implement` on every invocation.

## Target Users and Personas

- **Developer using `i2code go`** — runs the full idea-to-code workflow interactively from the terminal.

## Problem Statement and Goals

**Problem:** The `i2code go` orchestrator hard-codes `i2code implement "$dir"` with zero options (`idea-to-code.sh:266`). Users who want trunk mode or non-interactive execution must invoke `i2code implement` directly, bypassing the orchestrator.

**Goals:**

1. Allow the user to choose interactive vs non-interactive mode and worktree vs trunk mode before implementation starts.
2. Persist those choices in a config file so they don't need to be re-entered on subsequent runs.
3. Provide a way to reconfigure options without editing the config file manually.

## In-Scope

- Prompting the user for two options: interactive/non-interactive and worktree/trunk.
- Saving choices to `<idea-name>-implement-config.yaml` in the idea directory.
- Reading the config file and passing the corresponding CLI flags to `i2code implement`.
- Adding a "Configure implement options" menu item in the `has_plan` state.
- Defining a new `IMPLEMENT_CONFIG_FILE` variable in `_helper.sh`.

## Out-of-Scope

- Configuring other `i2code implement` options (e.g., `--isolate`, `--skip-ci-wait`, `--ci-fix-retries`, `--extra-prompt`).
- A Python-based config mechanism or new Python subcommand.
- Validating option compatibility (e.g., trunk + skip-ci-wait) — `i2code implement` already handles this.
- Migrating the `i2code go` shell script to Python.

## High-Level Functional Requirements

### FR1: Config File Convention

The config file is named `<idea-name>-implement-config.yaml` and stored in the idea directory, following the existing naming convention (`<idea-name>-*`).

The `_helper.sh` script defines a new variable `IMPLEMENT_CONFIG_FILE` alongside the existing file path variables.

### FR2: Config File Format

```yaml
interactive: true
trunk: false
```

Two boolean fields:
- `interactive` — `true` (default) for interactive mode, `false` for non-interactive (`--non-interactive`).
- `trunk` — `false` (default) for worktree mode, `true` for trunk mode (`--trunk`).

### FR3: First-Run Prompting

When the user selects "Implement the entire plan" and no config file exists, `i2code go` prompts for each option before starting implementation:

1. **Execution mode:** "How should Claude run?" with choices: `1) Interactive [default]` / `2) Non-interactive`.
2. **Branch strategy:** "Where should implementation happen?" with choices: `1) Worktree (branch + PR) [default]` / `2) Trunk (current branch, no PR)`.

After the user answers, the choices are written to the config file.

### FR4: Config-Driven Invocation

When the config file exists, `i2code go` reads it and builds the `i2code implement` command with the appropriate flags:

| Config Value | CLI Flag |
|---|---|
| `interactive: false` | `--non-interactive` |
| `trunk: true` | `--trunk` |

Default values (`interactive: true`, `trunk: false`) produce no additional flags, matching the current behavior.

### FR5: Reconfigure Menu Item

A new menu option is added to the `has_plan` state: "Configure implement options". Selecting it re-runs the prompting flow (FR3) and overwrites the config file. The menu becomes:

```
1) Revise the plan
2) Implement the entire plan
3) Configure implement options
4) Exit
```

The default selection remains `2` (Implement).

### FR6: Config Display Before Implementation

Before starting implementation, `i2code go` displays the active configuration:

```
Implementation options:
  Mode: interactive
  Branch: worktree
```

This gives the user a chance to see what will happen. It is informational only — there is no confirmation prompt.

## Non-Functional Requirements

### UX

- The prompting uses the existing `get_user_choice` function for consistency with the rest of the `i2code go` workflow.
- Config file is human-readable YAML that can be hand-edited if desired.
- Default options match current behavior (interactive + worktree), so existing workflows are not disrupted.

### Reliability

- If the config file is missing or unreadable at invocation time, fall back to prompting (FR3) rather than failing.
- If a config value is missing from the file, use the default for that value.

### Maintainability

- All prompting, reading, and writing logic lives in `idea-to-code.sh`, keeping the shell-based orchestrator self-contained.
- YAML parsing uses simple `grep`/`sed` patterns — the file has only two flat boolean fields, so a YAML library is not required.

## Success Metrics

- Users can run `i2code go` end-to-end in trunk mode or non-interactive mode without bypassing the orchestrator.
- Config file is created once and reused across subsequent runs of the same idea.

## Epics and User Stories

### Epic 1: Config File Infrastructure

**US1.1:** As a developer, I want `_helper.sh` to define `IMPLEMENT_CONFIG_FILE` so the config file path follows the project naming convention.

### Epic 2: Prompting and Persistence

**US2.1:** As a developer, when I select "Implement" for the first time on a project, I want to be prompted for interactive/non-interactive and worktree/trunk so I can choose my preferred execution style.

**US2.2:** As a developer, I want my choices saved to the config file so I am not prompted again on subsequent runs.

### Epic 3: Config-Driven Invocation

**US3.1:** As a developer, I want `i2code go` to read the config file and pass the corresponding flags to `i2code implement` so my preferences are honored.

**US3.2:** As a developer, I want to see the active config displayed before implementation starts so I know which mode will be used.

### Epic 4: Reconfigure

**US4.1:** As a developer, I want a "Configure implement options" menu item in the `has_plan` state so I can change my choices without editing the YAML file.

## User-Facing Scenarios

### Scenario 1: First-Time Implementation (Primary End-to-End Scenario)

The user has completed brainstorming, specification, and planning for a new idea. They select "Implement the entire plan" from the `has_plan` menu. No config file exists. `i2code go` prompts for execution mode (they choose non-interactive) and branch strategy (they choose trunk). The choices are saved to `<idea-name>-implement-config.yaml`. The active config is displayed. `i2code implement --non-interactive --trunk "$dir"` is invoked.

### Scenario 2: Subsequent Implementation Run

The user returns to an idea that has uncompleted tasks. The config file already exists with `interactive: true` and `trunk: false`. They select "Implement". The active config is displayed. `i2code implement "$dir"` is invoked with no extra flags (defaults).

### Scenario 3: Reconfiguring Options

The user previously chose worktree mode but now wants trunk mode. They select "Configure implement options" from the menu. They are prompted again and choose trunk. The config file is overwritten. They then select "Implement" and the new config is used.

### Scenario 4: Corrupt or Missing Config File

The user accidentally deletes or corrupts the config file. When they select "Implement", `i2code go` detects the missing/unreadable file and falls back to prompting, then saves a new config file.
