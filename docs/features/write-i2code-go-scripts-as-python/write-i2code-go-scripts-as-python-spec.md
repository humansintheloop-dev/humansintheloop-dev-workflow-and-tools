# Platform Capability Specification: Migrate i2code Bash Scripts to Python

## Purpose and Context

The `i2code` CLI has a hybrid architecture: some commands are implemented in Python, while others delegate to bash scripts via `script_command()` / `script_runner.py`. This migration eliminates all bash scripts from the codebase, replacing them with tested Python modules that follow the patterns already established by the `implement` command.

### Current State

The Python CLI (`cli.py`) registers 14 bash-backed commands through `script_command()`, which wraps each script as a Click command that delegates to `script_runner.py`. The scripts live in `src/i2code/scripts/` and share environment setup through `_helper.sh`.

The `implement` and `scaffold` commands are already pure Python, using constructor-based dependency injection (`command_assembler.py`), strategy pattern (`claude_runner.py`), and value objects (`IdeaProject`).

### Problem

- **Testability:** Bash tests in `test-scripts/` are fragile and limited in scope. Python's `pytest` enables unit tests, integration tests, mocking, and test coverage.
- **Maintainability:** `idea-to-code.sh` is 18KB with inline AWK validation, YAML parsing, and state machine logic — all difficult to reason about and modify.
- **Feature velocity:** Adding features to bash scripts is slow and error-prone compared to Python.
- **Consistency:** Half the codebase uses Python patterns (dependency injection, strategy, value objects); the other half is bash. This doubles the mental model.

### Target State

All CLI commands are implemented in Python. The `scripts/` directory, `script_command.py`, and `script_runner.py` are deleted. Each workflow step is a standalone Python function/class callable both from the `i2code go` orchestrator and from direct subcommands.

## Consumers

| Consumer | How They Use It |
|----------|----------------|
| `i2code go` users | Interactive orchestrator guiding idea → spec → plan → implement workflow |
| Direct subcommand users | `i2code spec create`, `i2code plan create`, etc. for individual steps |
| Test suite | pytest tests replacing bash test scripts |
| Future feature developers | Extend workflow steps without bash knowledge |

## Capabilities and Behaviors

### C1: Workflow Orchestrator (`i2code go`)

Replace `idea-to-code.sh` with a Python state machine that:

- **Detects workflow state** by checking file existence (idea, spec, plan files) — same logic as current bash, using `IdeaProject` for path derivation.
- **Presents numbered menus** via `input()` with the same options per state:
  - `no_idea`: Create idea
  - `has_idea_no_spec`: Revise idea / Create specification / Exit
  - `has_spec`: Revise spec / Create plan / Exit
  - `has_plan`: Revise plan / [Commit changes] / Implement / Configure / Exit
- **Manages implement configuration** — reads/writes `{name}-implement-config.yaml` (interactive and trunk boolean flags). Prompts on first run, reuses on subsequent runs.
- **Handles Ctrl+C** — catches `KeyboardInterrupt` and exits cleanly with code 130.
- **Handles step errors** — presents Retry/Abort menu on step failure.
- **Detects uncommitted changes** — shows "Commit changes" menu option when git status is dirty.

During the transition period, the orchestrator calls not-yet-migrated bash scripts via `script_runner.py`. Each call site is replaced with a direct Python function call when the corresponding script is migrated.

### C2: Idea Brainstorming (`i2code idea brainstorm`)

Replace `brainstorm-idea.sh` with Python that:

- Creates idea directory if needed.
- Detects and launches the user's editor (`code`, `$VISUAL`, `$EDITOR`, or `vi`) with a template.
- Manages session IDs — generates UUID for new sessions, resumes existing sessions via `--resume` flag.
- Invokes Claude with the `brainstorm-idea.md` prompt template.

### C3: Specification Creation (`i2code spec create`)

Replace `make-spec.sh` with Python that:

- Validates idea file exists (via `IdeaProject`).
- Loads `create-spec.md` prompt template with variable substitution.
- Manages Claude session (new or resumed).
- Invokes Claude with the rendered prompt.

### C4: Specification Revision (`i2code spec revise`)

Replace `revise-spec.sh` with Python that:

- Validates idea and spec files exist.
- Constructs revision prompt (currently inline, not template-based).
- Invokes Claude with the prompt.

### C5: Plan Creation (`i2code plan create`)

Replace `make-plan.sh` with Python that:

- Validates idea and spec files exist.
- Enumerates available plugin skills (replaces `list-plugin-skills.sh`).
- Loads `create-implementation-plan.md` prompt template with variable substitution.
- Invokes Claude in non-interactive mode (`-p` flag) to generate the plan.
- **Validates the plan** — rewrites the AWK-based validator as a Python function. Checks each task has required fields: `TaskType`, `Entrypoint`, `Observable`, `Evidence`.
- **Auto-repairs invalid plans** — if validation fails, invokes Claude again with repair instructions (one attempt).

### C6: Plan Revision (`i2code plan revise`)

Replace `revise-plan.sh` with Python that:

- Validates idea, spec, and plan files exist.
- Loads `revise-plan.md` prompt template with variable substitution.
- Invokes Claude with the rendered prompt.

### C7: Plugin Skill Enumeration

Replace `list-plugin-skills.sh` with a Python function that:

- Searches `$PLUGIN_CACHE_DIR` (default: `~/.claude/plugins/cache`) for installed skills.
- Lists subdirectories under `idea-to-code/skills/`.
- Returns comma-separated list prefixed with `idea-to-code:`.

### C8: Design Document Creation (`i2code design create`)

Replace `create-design-doc.sh` with Python that:

- Validates idea and spec files exist.
- Loads `create-design-doc.md` prompt template.
- Invokes Claude with the rendered prompt.

### C9: Session Analysis (`i2code improve analyze-sessions`)

Replace `analyze-sessions.sh` with Python that:

- Takes tracking directory argument.
- Loads `analyze-sessions.md` prompt template.
- Invokes Claude with the rendered prompt.

### C10: Summary Reports (`i2code improve summary-reports`)

Replace `create-summary-reports.sh` with Python that:

- Takes tracking directory and optional `--project-name` arguments.
- Finds projects with sessions from today.
- Generates per-project reports using `create-summary-report.md` template.

### C11: Issue Review (`i2code improve review-issues`)

Replace `review-issues.sh` with Python that:

- Loads `review-issues.md` prompt template.
- Invokes Claude with the rendered prompt.

### C12: Claude Files Management

Replace `update-claude-files-from-project.sh` (`i2code improve update-claude-files`), `update-project-claude-files.sh` (`i2code setup update-project`), and `setup-claude-files.sh` (`i2code setup claude-files`) with Python equivalents that:

- Load their respective prompt templates.
- Invoke Claude with the rendered prompts.

### C13: Shared Infrastructure

Replace `_helper.sh` by extending `IdeaProject` and creating supporting modules:

- **`IdeaProject` extensions** — Add any missing derived paths: `discussion_file`, `session_id_file`, `design_file`, `story_file`, `plan_with_stories_file`, `implement_config_file`.
- **Validation methods** — Add `validate_idea()`, `validate_spec()`, `validate_plan()`, etc. as methods on `IdeaProject`.
- **Template rendering** — A function that loads a prompt template from `prompt-templates/` and substitutes `$VARIABLE` placeholders using `string.Template`.
- **Session management** — Functions to read/write session ID files and build Claude `--resume`/`--session-id` flags.
- **Menu helper** — A reusable function for numbered-option menus using `input()`.

## High-Level APIs, Contracts, and Integration Points

### Internal Python API

Each workflow step is a callable Python function or class, following the command/assembler pattern:

```
# Each step is independently callable
brainstorm_idea(project: IdeaProject, session: SessionManager) -> None
create_spec(project: IdeaProject, session: SessionManager) -> None
revise_spec(project: IdeaProject) -> None
create_plan(project: IdeaProject) -> None
revise_plan(project: IdeaProject) -> None
```

The orchestrator composes these steps. Direct subcommands (`i2code spec create`, etc.) invoke them independently.

### Dependencies Injected via Assembler

Following the `command_assembler.py` pattern, each command's dependencies are wired up explicitly:

- `IdeaProject` — path derivation and file validation
- `ClaudeRunner` — Claude invocation (interactive or captured)
- Template renderer — prompt template loading and substitution
- Session manager — session ID persistence
- Menu presenter — `input()`-based numbered menus (injectable for testing)

### CLI Contract (Unchanged)

All existing CLI commands retain the same names, arguments, and behavior:

| Command | Arguments |
|---------|-----------|
| `i2code go <directory>` | Idea project directory |
| `i2code idea brainstorm <directory>` | Idea project directory |
| `i2code spec create <directory>` | Idea project directory |
| `i2code spec revise <directory>` | Idea project directory |
| `i2code plan create <directory>` | Idea project directory |
| `i2code plan revise <directory>` | Idea project directory |
| `i2code design create <directory>` | Idea project directory |
| `i2code improve analyze-sessions <dir>` | Tracking directory |
| `i2code improve summary-reports <dir> [--project-name NAME]` | Tracking directory |
| `i2code improve review-issues <dir>` | Tracking directory |
| `i2code improve update-claude-files <dir>` | Project directory |
| `i2code setup claude-files <dir>` | Project directory |
| `i2code setup update-project <dir>` | Project directory |

### Prompt Templates (Unchanged)

All files in `src/i2code/prompt-templates/` remain as-is. The `$VARIABLE` substitution syntax is compatible with Python's `string.Template`.

## Non-Functional Requirements

### NF1: Test Coverage

Every migrated capability must have pytest tests. Tests are written using TDD (outside-in: acceptance test first, then unit tests one layer at a time).

### NF2: No New Dependencies

The migration introduces no new Python package dependencies. It uses: `click` (existing), `string.Template` (stdlib), `subprocess` (stdlib), `input()` (builtin).

### NF3: Behavioral Equivalence

Each migrated script must produce the same observable behavior:
- Same CLI arguments and exit codes
- Same file I/O (reads/writes the same files in the same formats)
- Same Claude invocations (same prompts, same flags)
- Same interactive menus (same options, same numbering)

### NF4: Incremental Delivery

Each script migration is independently shippable. The system works correctly at every intermediate state (some scripts Python, some still bash).

### NF5: Code Health

All new Python code targets a CodeScene Code Health score of 10.0. CodeScene pre-commit safeguard runs before every commit.

## Scenarios and Workflows

### Migration Order

Scripts are migrated in this order, each as an independent deliverable:

**Phase 1: Core Orchestrator**
1. `idea-to-code.sh` → Python orchestrator (state machine, menus, config)
   - During this phase, the Python orchestrator calls remaining bash scripts via `script_runner.py`

**Phase 2: Workflow Scripts (in workflow order)**
2. `brainstorm-idea.sh` → Python (editor launch, session mgmt, Claude)
3. `make-spec.sh` → Python (template, session, Claude)
4. `revise-spec.sh` → Python (prompt, Claude)
5. `make-plan.sh` → Python (template, validation, auto-repair, Claude)
6. `revise-plan.sh` → Python (template, Claude)
7. `list-plugin-skills.sh` → Python function (plugin enumeration)

**Phase 3: Utility Scripts**
8. `create-design-doc.sh` → Python
9. `analyze-sessions.sh` → Python
10. `create-summary-reports.sh` → Python
11. `review-issues.sh` → Python
12. `update-claude-files-from-project.sh` → Python
13. `update-project-claude-files.sh` → Python
14. `setup-claude-files.sh` → Python

**Phase 4: Cleanup**
15. Delete `_helper.sh`, `script_command.py`, `script_runner.py`, `scripts/` directory
16. Delete all bash test scripts in `test-scripts/` that tested migrated scripts

### Primary End-to-End Scenario: Migrate the Orchestrator

This is the highest-risk, highest-value migration — `idea-to-code.sh` is the largest script (18KB) and the entry point for the entire workflow.

**Preconditions:**
- All bash scripts exist and work as today
- `IdeaProject` value object exists with basic path derivation

**Steps:**
1. Extend `IdeaProject` with all missing derived paths and validation methods
2. Create a menu helper module (numbered options via `input()`)
3. Create a template renderer using `string.Template`
4. Create the orchestrator as a Python class using the command/assembler pattern
5. Implement state detection (file existence checks via `IdeaProject`)
6. Implement each state's menu and transitions
7. Implement implement-config management (read/write YAML, prompt, build flags)
8. Implement error handling (retry/abort menu) and signal handling (`KeyboardInterrupt`)
9. Wire subprocess calls to remaining bash scripts via `script_runner.py`
10. Replace the `script_command(main, "go", "idea-to-code.sh", ...)` registration with a direct Click command that invokes the Python orchestrator
11. Delete `idea-to-code.sh`
12. Delete corresponding bash tests; replace with pytest tests

**Postconditions:**
- `i2code go <dir>` runs the Python orchestrator
- The orchestrator calls remaining bash scripts via `script_runner.py`
- All orchestrator behavior is covered by pytest tests
- Bash tests for the orchestrator are deleted

### Scenario: Migrate a Simple Workflow Script (make-spec.sh)

Representative of the simpler scripts (C3, C4, C6, C8–C12).

**Steps:**
1. Create a Python function for spec creation using assembler pattern
2. Load and render the `create-spec.md` template via `string.Template`
3. Handle session management (new/resume)
4. Invoke Claude via `ClaudeRunner`
5. Register as a direct Click command (replacing `script_command` registration)
6. Update the orchestrator to call the Python function instead of `script_runner.py`
7. Delete `make-spec.sh` and its bash tests

### Scenario: Migrate the Plan Creator (make-plan.sh)

The most complex workflow script due to AWK validation and auto-repair.

**Steps:**
1. Create a Python function for plan creation
2. Rewrite the AWK plan validator as a Python function
3. Implement the auto-repair loop (validate → if fail, invoke Claude for repair → validate again)
4. Integrate plugin skill enumeration (replaces `list-plugin-skills.sh`)
5. Register as a direct Click command
6. Update the orchestrator call site
7. Delete `make-plan.sh` and `list-plugin-skills.sh`

## Constraints and Assumptions

### Constraints

- **No user-facing behavior change.** CLI commands, arguments, menus, and output must remain the same.
- **No prompt template changes.** The `$VARIABLE` syntax in `prompt-templates/` is compatible with `string.Template`.
- **No new dependencies.** Only stdlib and existing packages (`click`).
- **Incremental delivery.** The system must work at every intermediate state during migration.
- **TDD.** All code is developed test-first using outside-in TDD with pytest.

### Assumptions

- The `claude` CLI is invoked via `subprocess` (same as today). No Python SDK integration.
- The existing `ClaudeRunner` from the `implement` command can be reused or adapted for the workflow scripts' needs (interactive mode, session management, non-interactive mode with output capture).
- `IdeaProject` can be extended with new properties without breaking existing consumers.
- Bash test scripts that test migrated functionality can be safely deleted after pytest equivalents exist.

## Acceptance Criteria

### Per-Script Migration

For each migrated script:

1. The Python implementation passes all pytest tests covering the script's behavior.
2. The CLI command (`i2code <subcommand>`) works identically to the bash version.
3. The `i2code go` orchestrator correctly invokes the Python version.
4. The bash script and its bash tests are deleted.
5. CodeScene Code Health score is 10.0 for all new Python files.

### Full Migration Complete

1. The `src/i2code/scripts/` directory is deleted.
2. `script_command.py` and `script_runner.py` are deleted.
3. No `.sh` files remain in the production codebase under `src/`.
4. All CLI commands work identically to pre-migration behavior.
5. All behavior is covered by pytest tests.
6. `i2code go` runs entirely in Python with no subprocess calls to bash scripts.
