The sandbox restricts access to files outside the current idea directory. The spec is detailed enough to generate the plan. Let me produce it based on the idea and specification.

# Implementation Plan: i2code go Implementation Options Configuration

## Idea Type

**A. User-facing feature** — This is a user-facing UX improvement to the `i2code go` interactive menu system.

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Key Source Files

Before starting, read these files to understand the current codebase:

- `src/i2code/idea_cmd/orchestrator.py` — Contains `_build_has_plan_options()`, `_commit_default()`, `_ensure_implement_config()`, `_configure_implement()`, `_display_implement_config()`
- `src/i2code/implement/implement_config.py` — Contains `prompt_implement_config()`, `read_implement_config()`, `write_implement_config()`, `build_implement_flags()`, `build_implement_label()`
- `src/i2code/implement/implement_opts.py` — Contains `ImplementOpts` and isolation type definitions
- `tests/idea-cmd/` — Existing orchestrator tests
- `tests/implement/` — Existing implement config tests

Run `grep -r "CONFIGURE_IMPLEMENT" src/` to find the constant definition and all usages.

---

## Steel Thread 1: Isolation Type in Config File (Read/Write/Flags)

This thread adds `isolation_type` support to the config data layer — reading, writing, building flags, and building the menu label — without touching the orchestrator menu yet. All tasks use TDD.

- [x] **Task 1.1: read_implement_config returns isolation_type with backward compatibility**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/implement/`
  - Observable: `read_implement_config()` returns a dict with three keys (`interactive`, `isolation_type`, `trunk`). When `isolation_type` is missing from the YAML file, it defaults to `"none"`.
  - Evidence: pytest runs tests that (a) read a config with all three fields and verify the dict, (b) read a legacy config with only `interactive` and `trunk` and verify `isolation_type` defaults to `"none"`.
  - Steps:
    - [x] Read `src/i2code/implement/implement_config.py` to understand current `read_implement_config()` signature and return type
    - [x] Read existing tests in `tests/implement/` for implement_config to understand test patterns
    - [x] Write failing tests for: (a) reading a config with `isolation_type: nono` returns all three fields, (b) reading a legacy config missing `isolation_type` returns `isolation_type: "none"`
    - [x] Update `read_implement_config()` to include `isolation_type` in the returned dict, defaulting to `"none"` if missing

- [x] **Task 1.2: write_implement_config writes isolation_type field**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/implement/`
  - Observable: `write_implement_config(path, interactive, isolation_type, trunk)` writes a YAML file containing all three fields.
  - Evidence: pytest runs a test that calls `write_implement_config()` with `isolation_type="nono"` and verifies the written file contains `isolation_type: nono`.
  - Steps:
    - [x] Write failing test that calls `write_implement_config()` with all three args and reads back the file to verify `isolation_type` is present
    - [x] Update `write_implement_config()` signature to accept `isolation_type` parameter and write it to the YAML file
    - [x] Update all callers of `write_implement_config()` (search with `grep -r "write_implement_config" src/`) to pass `isolation_type`

- [x] **Task 1.3: build_implement_flags includes --isolation-type flag**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/implement/`
  - Observable: `build_implement_flags(config)` returns `--isolation-type {value}` when `isolation_type` is not `"none"`, and omits it when `isolation_type` is `"none"`.
  - Evidence: pytest runs tests with configs containing various isolation types and verifies the flag list.
  - Steps:
    - [x] Write failing tests: (a) config with `isolation_type: "nono"` produces `["--isolation-type", "nono"]` in flags, (b) config with `isolation_type: "none"` does NOT include `--isolation-type` in flags, (c) config with `isolation_type: "container"` and `interactive: false` produces both `--non-interactive` and `--isolation-type container`
    - [x] Update `build_implement_flags()` to emit `--isolation-type {value}` when isolation_type is not `"none"`

- [x] **Task 1.4: build_implement_label reflects isolation_type in menu text**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/implement/`
  - Observable: `build_implement_label(config_path)` includes `--isolation-type {value}` in the label string when isolation type is not "none". Examples: `"Implement the entire plan: i2code implement --non-interactive --isolation-type nono"`.
  - Evidence: pytest runs tests with different config files and verifies the label string.
  - Steps:
    - [x] Write failing tests: (a) config with defaults produces `"Implement the entire plan: i2code implement"`, (b) config with `isolation_type: "nono"` and `interactive: false` produces `"Implement the entire plan: i2code implement --non-interactive --isolation-type nono"`, (c) no config file produces `"Implement the entire plan: i2code implement"`
    - [x] Update `build_implement_label()` to use the updated `build_implement_flags()` (likely already works if flags are correct, but verify)

---

## Steel Thread 2: Config Prompt Asks Isolation Type (US2.1, US2.2, US2.3)

This thread adds the isolation type question to the interactive prompt flow.

- [x] **Task 2.1: prompt_implement_config asks isolation type and conditionally skips trunk question**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/implement/`
  - Observable: `prompt_implement_config(menu_fn)` asks three questions in order: mode, isolation type, branch strategy. When isolation type is not "none", it skips the branch strategy question and sets trunk to `false`. Returns `(interactive, isolation_type, trunk)`.
  - Evidence: pytest runs tests with injected `menu_fn` that simulate: (a) selecting isolation "none" → all three questions asked, returns `(True, "none", False)`, (b) selecting isolation "nono" → trunk question skipped, returns `(True, "nono", False)`, (c) selecting non-interactive + VM → returns `(False, "vm", False)`
  - Steps:
    - [x] Read current `prompt_implement_config()` in `src/i2code/implement/implement_config.py` to understand how `menu_fn` is called
    - [x] Write failing tests with injected `menu_fn` for the three scenarios described in Evidence
    - [x] Update `prompt_implement_config()` to: (a) add isolation type question after mode question with choices `["None", "Nono", "Container", "VM"]`, (b) conditionally ask branch strategy only when isolation is "none", (c) return 3-tuple `(interactive, isolation_type, trunk)`
    - [x] Update return type annotation if type hints are used

---

## Steel Thread 3: Menu Restructuring (US1.1, US1.2, US1.3)

This thread restructures the HAS_PLAN menu in the orchestrator to always show configure/revise and set correct defaults.

- [x] **Task 3.1: HAS_PLAN menu always shows configure/revise option at position 2**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/`
  - Observable: `_build_has_plan_options()` always includes "Configure implement options" (when no config exists) or "Revise implement options" (when config exists) at position 2. Menu order is: Revise plan, Configure/Revise options, Move (conditional), Commit (conditional), Implement, Exit.
  - Evidence: pytest runs tests that verify the menu list returned by `_build_has_plan_options()` for: (a) no config file → "Configure implement options" at index 1, (b) config file exists → "Revise implement options" at index 1, (c) both cases have correct relative ordering of all items.
  - Steps:
    - [x] Read `src/i2code/idea_cmd/orchestrator.py` to understand `_build_has_plan_options()` and the `CONFIGURE_IMPLEMENT` constant
    - [x] Read existing orchestrator tests to understand test patterns and `OrchestratorDeps` injection
    - [x] Write failing tests for the three scenarios in Evidence
    - [x] Update `_build_has_plan_options()` to always include the configure/revise option at position 2, using label "Configure implement options" or "Revise implement options" based on config file existence
    - [x] Ensure the "Implement" label uses the updated `build_implement_label()` that reflects isolation type

- [x] **Task 3.2: Default menu selection is configure when no config exists**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/`
  - Observable: When no config file exists, the default selection is "Configure implementation options" (position 2). When config exists and there are uncommitted changes, default is "Commit changes". When config exists and no uncommitted changes, default is "Revise implementation options".
  - Evidence: pytest runs tests that verify `_commit_default()` (or equivalent) returns the correct default for each condition.
  - Steps:
    - [x] Write failing tests for the three default-selection scenarios
    - [x] Update `_commit_default()` to return the configure option as default when no config file exists, and the commit option when config exists with uncommitted changes

---

## Steel Thread 4: Orchestrator Wiring for Three-Field Config (US3.2, FR9)

This thread updates the orchestrator methods that call prompt/read/write to handle the three-field config tuple.

- [x] **Task 4.1: _ensure_implement_config and _configure_implement pass isolation_type**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/`
  - Observable: `_ensure_implement_config()` and `_configure_implement()` correctly receive the 3-tuple from `prompt_implement_config()` and pass `isolation_type` to `write_implement_config()`. The written config file contains all three fields.
  - Evidence: pytest runs tests that simulate the configure flow and verify the written config file contains `isolation_type`.
  - Steps:
    - [x] Write failing tests that trigger `_ensure_implement_config()` via the menu and verify the config file written contains `isolation_type`
    - [x] Update `_ensure_implement_config()` to unpack 3-tuple `(interactive, isolation_type, trunk)` from `prompt_implement_config()` and pass all three to `write_implement_config()`
    - [x] Update `_configure_implement()` similarly
    - [x] Update `_display_implement_config()` to show isolation type (per FR8: `Isolation: {value}`)

---

## Steel Thread 5: Display Config Shows Isolation Type (FR8)

- [ ] **Task 5.1: _display_implement_config shows isolation type**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/`
  - Observable: `_display_implement_config(config)` prints `Isolation: {value}` alongside Mode and Branch.
  - Evidence: pytest runs a test that captures stdout from `_display_implement_config()` with `isolation_type: "nono"` and asserts the output contains `Isolation: nono`.
  - Steps:
    - [ ] Write failing test that calls `_display_implement_config()` with a config dict containing `isolation_type: "nono"` and verifies stdout contains `Isolation: nono`
    - [ ] Update `_display_implement_config()` to include the isolation type line

---

## Change History
### 2026-03-13 17:01 - mark-task-complete
write_implement_config now accepts and writes isolation_type field; all callers updated

### 2026-03-13 17:07 - mark-task-complete
build_implement_flags emits --isolation-type flag when isolation_type is not none

### 2026-03-13 17:11 - mark-task-complete
build_implement_label includes isolation_type in menu text via build_implement_flags delegation

### 2026-03-13 17:14 - mark-step-complete
Read current prompt_implement_config implementation

### 2026-03-13 17:16 - mark-step-complete
Wrote failing tests for three isolation scenarios

### 2026-03-13 17:16 - mark-step-complete
Updated prompt_implement_config with isolation question and conditional branch strategy

### 2026-03-13 17:16 - mark-step-complete
Updated return type annotation in docstring

### 2026-03-13 17:17 - mark-task-complete
prompt_implement_config now asks isolation type and conditionally skips trunk question

### 2026-03-13 17:22 - mark-step-complete
Read orchestrator.py - understood _build_has_plan_options and CONFIGURE_IMPLEMENT

### 2026-03-13 17:22 - mark-step-complete
Read test_orchestrator_lifecycle_menu.py - understood _build_menu_options pattern with menu_config_by_label and OrchestratorDeps

### 2026-03-13 17:23 - mark-step-complete
Wrote 5 failing tests covering no-config, config-exists, and ordering scenarios

### 2026-03-13 17:25 - mark-step-complete
Updated _build_has_plan_options to always include configure/revise at position 2, with dynamic label via _configure_implement_label()

### 2026-03-13 17:26 - mark-step-complete
build_implement_label already reflects isolation_type from thread 2 work - verified in _build_has_plan_options line 308

### 2026-03-13 17:26 - mark-task-complete
HAS_PLAN menu always shows configure/revise option at position 2 with dynamic label

### 2026-03-13 17:35 - mark-step-complete
Tests written for three default-selection scenarios

### 2026-03-13 17:36 - mark-step-complete
Updated _commit_default to return position 2 when no commit option exists

### 2026-03-13 17:37 - mark-task-complete
Default selection now returns configure/revise at position 2, or commit when dirty

### 2026-03-14 09:59 - mark-task-complete
Tests verify isolation_type flows through _ensure_implement_config, _configure_implement, and _display_implement_config
