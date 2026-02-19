# Specification: Package Workflow Scripts as i2code Subcommands

## Purpose and Background

The `i2code` CLI currently has Python-based subcommands for plan management (`i2code plan`) and implementation (`i2code implement`). However, the broader idea-to-code workflow — brainstorming, specification creation, plan generation, design documentation, session analysis, and project setup — is driven by standalone shell scripts in `workflow-scripts/`.

These scripts are not installable, require users to know their filesystem paths, and lack a unified invocation pattern. This feature packages them as `i2code` subcommands, making the entire workflow accessible through a single, `uv`-installable CLI.

## Target Users and Personas

**Primary persona: Developer using the idea-to-code workflow.**
A developer who uses Claude and the idea-to-code process to go from a rough idea to a working implementation. They already have `i2code` installed via `uv` and expect all workflow tools to be available through it.

## Problem Statement and Goals

**Problem:** Workflow scripts are loosely organized in a `workflow-scripts/` directory. Users must know file paths and call scripts directly (e.g., `./workflow-scripts/brainstorm-idea.sh <dir>`). They are not installable as a package and cannot be used outside the repository.

**Goals:**
1. All workflow scripts are invocable as `i2code <group> <subcommand>` commands.
2. The entire CLI (including bundled scripts and prompt templates) is installable via `uv`.
3. Existing script behavior is preserved — no functional changes to the shell scripts.
4. The original `workflow-scripts/` directory is removed after migration.

## In-Scope

- Packaging 13 shell scripts as `i2code` subcommands across 4 new Click groups, 1 top-level command, and 2 additions to the existing `plan` group
- Bundling `_helper.sh` and prompt templates as package data
- Creating a helper script to discover plugin skill names from `~/.claude/plugins/cache/`
- Modifying 3 scripts to accept `config-files/` as a script argument
- Updating `pyproject.toml` to include package data
- Removing `workflow-scripts/` after migration

## Out-of-Scope

- Rewriting shell scripts in Python (future work)
- Converting `implement-todo-list.sh` and `refine-todo-list.sh` (deferred)
- Converting `implement-plan.sh` or `implement-with-worktree.sh` (already replaced by `i2code implement`)
- Adding new functionality to any script
- Changing the Click wrapper beyond minimal passthrough

## High-Level Functional Requirements

### FR1: CLI Group Structure

Four new Click groups and one top-level command are added to the `i2code` CLI:

| Group/Command | Purpose |
|---|---|
| `go` | Top-level orchestrator command — runs the full idea-to-code workflow |
| `idea` | Brainstorm and explore ideas |
| `spec` | Create and revise specifications |
| `design` | Create design documents |
| `improve` | Analyze sessions, review issues, and update configuration |
| `setup` | Initial project setup and configuration updates |

Two new subcommands are added to the existing `plan` group:

| Subcommand | Purpose |
|---|---|
| `plan create` | Create an implementation plan from a specification |
| `plan revise` | Revise an existing implementation plan |

The naming follows a consistent `<artifact> <verb>` pattern for artifact-focused groups (`idea`, `spec`, `plan`, `design`), creating a clear workflow progression: `idea` → `spec` → `plan` → `design` → `implement`.

### FR2: Subcommand Mapping

#### `i2code go` (top-level command)

| Command | Source Script | Arguments |
|---|---|---|
| `go` | `idea-to-code.sh` | `<idea-directory>` |

#### `i2code idea` (1 subcommand)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `brainstorm` | `brainstorm-idea.sh` | `<idea-directory>` |

#### `i2code spec` (2 subcommands)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `create` | `make-spec.sh` | `<idea-directory>` [claude-args...] |
| `revise` | `revise-spec.sh` | `<idea-directory>` |

#### `i2code plan` (2 new subcommands added to existing group)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `create` | `make-plan.sh` | `<idea-directory>` [claude-args...] |
| `revise` | `revise-plan.sh` | `<idea-directory>` |

#### `i2code design` (1 subcommand)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `create` | `create-design-doc.sh` | `<idea-directory>` [claude-args...] |

#### `i2code improve` (4 subcommands)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `analyze-sessions` | `analyze-sessions.sh` | `<project-tracking-dir>` |
| `summary-reports` | `create-summary-reports.sh` | `<hitl-tracking-dir>` [--project-name NAME] |
| `review-issues` | `review-issues.sh` | `<hitl-tracking-dir>` [--project NAME] [-- claude-args...] |
| `update-claude-files` | `update-claude-files-from-project.sh` | `<project-dir>` [claude-args...] |

#### `i2code setup` (2 subcommands)

| Subcommand | Source Script | Arguments |
|---|---|---|
| `claude-files` | `setup-claude-files.sh` | `--config-dir <path>` |
| `update-project` | `update-project-claude-files.sh` | `<project-dir>` `--config-dir <path>` [claude-args...] |

### FR3: Click Wrapper Behavior

Each Click command:
1. Locates the bundled shell script using `importlib.resources` or `__file__`-relative path resolution.
2. Forwards all arguments to the shell script via `subprocess.run()`.
3. Propagates the shell script's exit code.
4. Does **not** parse, validate, or transform arguments — the shell script handles everything.

### FR4: Package Data Layout

```
src/i2code/
├── scripts/              # Bundled shell scripts (from workflow-scripts/)
│   ├── _helper.sh
│   ├── brainstorm-idea.sh
│   ├── idea-to-code.sh
│   ├── make-spec.sh
│   ├── make-plan.sh
│   ├── revise-spec.sh
│   ├── revise-plan.sh
│   ├── create-design-doc.sh
│   ├── analyze-sessions.sh
│   ├── create-summary-reports.sh
│   ├── review-issues.sh
│   ├── update-claude-files-from-project.sh
│   ├── setup-claude-files.sh
│   ├── update-project-claude-files.sh
│   └── list-plugin-skills.sh   # New helper script
├── prompt-templates/     # Bundled prompt templates (from prompt-templates/)
│   ├── brainstorm-idea.md
│   ├── create-spec.md
│   ├── create-implementation-plan.md
│   ├── revise-plan.md
│   ├── create-design-doc.md
│   ├── analyze-sessions.md
│   ├── create-summary-report.md
│   ├── review-issues.md
│   ├── update-claude-files-from-project.md
│   └── update-project-claude-files.md
├── cli.py                # Updated: registers new groups and top-level go command
├── idea_cmd/             # New: Click group for idea brainstorming
│   └── cli.py
├── spec_cmd/             # New: Click group for spec create/revise
│   └── cli.py
├── design_cmd/           # New: Click group for design document creation
│   └── cli.py
├── improve/              # New: Click group + subcommands
│   └── cli.py
├── setup_cmd/            # New: Click group + subcommands
│   └── cli.py
├── plan/                 # Existing: gains create and revise subcommands
│   └── cli.py
└── ...                   # Existing packages (implement/, tracking/)
```

The `scripts/` and `prompt-templates/` directories are siblings under `src/i2code/`, preserving the existing `$DIR/../prompt-templates/` path references in the shell scripts without modification.

### FR5: Script Modifications

#### Config directory as argument

Three scripts currently derive `config-files/` from `$DIR/..`. They must be modified to accept it as an argument:

- `setup-claude-files.sh` — new required argument: config directory path
- `update-project-claude-files.sh` — new required argument: config directory path
- `update-claude-files-from-project.sh` — new required argument: config directory path

#### Skill name discovery

A new helper script `list-plugin-skills.sh` is created that:
1. Searches `~/.claude/plugins/cache/` for the `idea-to-code` plugin directory.
2. Lists subdirectory names under the plugin's `skills/` directory.
3. Formats them as `idea-to-code:<skill-name>` comma-separated.
4. Returns the formatted string to stdout.

Two scripts are modified to call this helper instead of `ls -1 "$DIR/../skills"`:
- `make-plan.sh`
- `create-design-doc.sh`

### FR6: pyproject.toml Updates

The `[tool.hatch.build.targets.wheel]` section must include the `scripts/` and `prompt-templates/` directories as package data so they are included in the installed wheel.

### FR7: Removal of workflow-scripts/

After all scripts are migrated and verified:
- `workflow-scripts/` directory is deleted.
- `_python_helper.sh` and `requirements.txt` are not migrated (dead code).
- `implement-plan.sh` and `implement-with-worktree.sh` are not migrated (already replaced).
- `implement-todo-list.sh` and `refine-todo-list.sh` are not migrated (deferred).

## Security Requirements

This feature is a local CLI tool with no network-facing endpoints. All operations run with the invoking user's filesystem permissions. No additional authorization checks are required.

## Non-Functional Requirements

### NFR1: Behavioral Equivalence
Every subcommand must produce identical behavior to directly invoking the original shell script. No functional changes.

### NFR2: Installability
`uv tool install .` (or `uv pip install .`) from the project root must produce a working `i2code` binary with all new subcommands functional and shell scripts accessible.

### NFR3: Shell Script Executability
Bundled `.sh` files must retain their execute permission in the installed package. If the build system strips permissions, the Click wrapper must ensure executability before invoking.

### NFR4: Graceful Degradation for Skill Discovery
If the `idea-to-code` plugin is not installed in `~/.claude/plugins/cache/`, the `list-plugin-skills.sh` helper should print a warning to stderr and output an empty string, allowing `make-plan.sh` and `create-design-doc.sh` to proceed without skill names in prompts.

## Success Metrics

1. All 13 subcommands are invocable and produce the same output as their source scripts.
2. `uv tool install .` installs a working CLI with all subcommands.
3. `workflow-scripts/` directory is removed from the repository.
4. `i2code --help` shows the new groups alongside existing ones.

## Epics and User Stories

### Epic 1: Package Data Infrastructure

**US1.1:** As a developer, I want shell scripts and prompt templates bundled as package data in `src/i2code/scripts/` and `src/i2code/prompt-templates/` so they are included in the installed package.

**US1.2:** As a developer, I want `pyproject.toml` updated to include the new package data directories so `hatchling` bundles them in the wheel.

### Epic 2: Workflow Subcommands (go, idea, spec, plan, design)

**US2.1:** As a developer, I want to run `i2code go <dir>` to launch the interactive orchestrator that guides me through the full workflow.

**US2.2:** As a developer, I want to run `i2code idea brainstorm <dir>` to brainstorm an idea, so I don't need to know the script path.

**US2.3:** As a developer, I want to run `i2code spec create <dir>` to generate a specification from an idea.

**US2.4:** As a developer, I want to run `i2code spec revise <dir>` to revise an existing specification.

**US2.5:** As a developer, I want to run `i2code plan create <dir>` to generate an implementation plan from a specification.

**US2.6:** As a developer, I want to run `i2code plan revise <dir>` to revise an existing plan.

**US2.7:** As a developer, I want to run `i2code design create <dir>` to generate a design document.

### Epic 3: improve Subcommands

**US3.1:** As a developer, I want to run `i2code improve analyze-sessions <tracking-dir>` to analyze project tracking sessions.

**US3.2:** As a developer, I want to run `i2code improve summary-reports <hitl-dir>` to generate summary reports from today's sessions.

**US3.3:** As a developer, I want to run `i2code improve review-issues <hitl-dir>` to review and incorporate active issue feedback.

**US3.4:** As a developer, I want to run `i2code improve update-claude-files <project-dir>` to update shared config from project-specific improvements.

### Epic 4: setup Subcommands

**US4.1:** As a developer, I want to run `i2code setup claude-files --config-dir <path>` to copy initial Claude config files into my project.

**US4.2:** As a developer, I want to run `i2code setup update-project <project-dir> --config-dir <path>` to push template updates into a project's Claude files.

### Epic 5: Script Modifications

**US5.1:** As a developer, I want `make-plan.sh` and `create-design-doc.sh` to discover skill names from the installed plugin cache so they work when bundled as package data.

**US5.2:** As a developer, I want `setup-claude-files.sh`, `update-project-claude-files.sh`, and `update-claude-files-from-project.sh` to accept `config-dir` as a script argument so they work independently of their filesystem location.

### Epic 7: Command Renaming

**US7.1:** As a developer, I want the `idea-to-plan` group replaced with `go`, `idea`, `spec`, `plan`, and `design` commands so the CLI follows a consistent `<artifact> <verb>` naming pattern.

### Epic 6: Cleanup

**US6.1:** As a developer, I want `workflow-scripts/` removed from the repository after migration so there is a single source of truth for these scripts.

## User-Facing Scenarios

### Scenario 1: Full Idea-to-Plan Workflow (Primary End-to-End)

A developer has a new feature idea. They run:
```
i2code go docs/features/my-feature
```
The orchestrator detects no idea file exists, launches brainstorming, then walks them through spec creation and plan generation — the same interactive flow as `idea-to-code.sh` today.

### Scenario 2: Individual Step Invocation

A developer already has an idea and spec. They skip the orchestrator and run:
```
i2code plan create docs/features/my-feature
```
This generates the implementation plan directly.

### Scenario 3: Session Analysis and Improvement

After a day of development, a developer runs:
```
i2code improve summary-reports ~/hitl-tracking --project-name my-project
i2code improve review-issues ~/hitl-tracking --project my-project
```
These analyze the day's sessions and review filed issues.

### Scenario 4: Project Setup

A developer sets up Claude files in a new project:
```
i2code setup claude-files --config-dir /path/to/genai-development-workflow/config-files
```

### Scenario 5: Install and Discover

A developer installs the tool and explores available commands:
```
uv tool install .
i2code --help
i2code idea --help
i2code spec --help
i2code plan --help
i2code design --help
i2code improve --help
i2code setup --help
```
All groups and subcommands appear with short descriptions.
