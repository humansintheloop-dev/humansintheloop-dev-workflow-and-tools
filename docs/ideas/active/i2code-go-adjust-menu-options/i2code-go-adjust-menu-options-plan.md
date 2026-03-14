Now I have everything I need. Here's the plan:

---

# Implementation Plan: Adjust HAS_PLAN Menu Options to Follow Natural Workflow

## Idea Type

**D. User-facing feature** — Changes default selection behavior of the interactive `i2code go` CLI menu based on lifecycle state.

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

---

## Key Files

| File | Role |
|------|------|
| `src/i2code/go_cmd/orchestrator.py` | Production code: `_build_has_plan_options()` (line 311), `_commit_default()` (line 329), `_lifecycle_move_label()` (line 298) |
| `src/i2code/idea/metadata.py` | `read_metadata()` — reads YAML metadata file |
| `src/i2code/implement/idea_project.py` | `IdeaProject` — provides `metadata_file` path |
| `tests/go-cmd/test_orchestrator_default_selection.py` | Tests for default selection (currently config-based, must become lifecycle-aware) |
| `tests/go-cmd/test_orchestrator_lifecycle_menu.py` | Tests for lifecycle menu options and their positions |
| `tests/go-cmd/conftest.py` | Shared fixtures: `TempIdeaProject`, `menu_config_by_label` |

## Design Notes

**Current behavior:** `_commit_default()` returns the index of "Commit changes" if uncommitted changes exist, otherwise falls back to option 2 (Configure/Revise implement options). It ignores lifecycle state entirely.

**Target behavior:** Replace `_commit_default()` with a lifecycle-aware method that reads metadata state and returns the appropriate default based on the table in FR-2. The method should reuse the metadata already read by `_lifecycle_move_label()` to avoid duplicate file I/O.

**Refactoring approach:** Extract metadata reading into a shared call so both `_lifecycle_move_label()` and the new default logic use the same metadata dict, read once per menu build. This can be done by reading metadata in `_build_has_plan_options()` and passing the state to both methods.

All steps should be implemented using TDD.

---

## Steel Thread 1: Lifecycle-Aware Default Selection

This thread replaces `_commit_default()` with lifecycle-aware logic. The option order in `_build_has_plan_options()` already matches the spec, so no reordering is needed — only the default selection logic changes.

### Task 1.1: Draft state defaults to "Move idea to ready"

- [x] **Task 1.1: Draft state defaults to "Move idea to ready"**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <idea-in-draft-state>` (menu presentation)
  - Observable: When idea is in `draft` state, the default menu option is "Move idea to ready" instead of "Configure implement options"
  - Evidence: `pytest tests/go-cmd/test_orchestrator_default_selection.py tests/go-cmd/test_orchestrator_lifecycle_menu.py -v` passes with new/updated tests asserting draft state defaults to "Move idea to ready"
  - Steps:
    - [ ] Update `tests/go-cmd/test_orchestrator_lifecycle_menu.py`: Change `TestDraftIdeaMenu.test_draft_idea_no_config_defaults_to_configure` to assert default is `MOVE_TO_READY` instead of `CONFIGURE_IMPLEMENT`. Rename to `test_draft_idea_defaults_to_move_to_ready`.
    - [ ] Add a new test in `TestDraftIdeaMenu`: `test_draft_idea_with_uncommitted_changes_defaults_to_move_to_ready` — verifies that even with dirty git, draft state defaults to "Move idea to ready" (lifecycle takes precedence over uncommitted changes).
    - [ ] In `src/i2code/go_cmd/orchestrator.py`, refactor metadata reading: extract a `_read_lifecycle_state()` method that reads metadata and returns the state string (or `None`). Have `_lifecycle_move_label()` call `_read_lifecycle_state()` internally.
    - [ ] Replace `_commit_default()` with `_lifecycle_default(options)` that calls `_read_lifecycle_state()` and implements the default logic table. For now, handle the `draft` case: if state is `"draft"` and `MOVE_TO_READY` is in options, return its 1-based index. Otherwise fall back to option 2.
    - [ ] Update the caller at `src/i2code/go_cmd/orchestrator.py:270` to call `_lifecycle_default(options)` instead of `_commit_default(options)`.
    - [ ] Run tests to verify draft default changed and no regressions.

### Task 1.2: Ready state defaults to "Configure/Revise implement options"

- [x] **Task 1.2: Ready state defaults to "Configure/Revise implement options"**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <idea-in-ready-state>` (menu presentation)
  - Observable: When idea is in `ready` state, the default menu option is "Configure implement options" (or "Revise implement options" if config exists)
  - Evidence: `pytest tests/go-cmd/test_orchestrator_lifecycle_menu.py::TestReadyIdeaMenu -v` passes with updated test asserting ready state defaults to configure/revise
  - Steps:
    - [x] In `tests/go-cmd/test_orchestrator_lifecycle_menu.py`, rename `TestReadyIdeaMenu.test_ready_idea_no_config_defaults_to_configure` to `test_ready_idea_defaults_to_configure` (this test already passes since option 2 is configure, but verifying it still works with new logic).
    - [x] Add `test_ready_idea_with_config_defaults_to_revise` — verifies that with an existing config file, default is `REVISE_IMPLEMENT`.
    - [x] In `_lifecycle_default()`, add the `"ready"` case: return the 1-based index of the configure/revise label (which is always option 2).
    - [x] Run tests.

### Task 1.3: WIP state defaults based on uncommitted changes

- [x] **Task 1.3: WIP state defaults to "Commit changes" or "Implement the entire plan"**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <idea-in-wip-state>` (menu presentation)
  - Observable: When idea is in `wip` state with uncommitted changes, default is "Commit changes". When no uncommitted changes, default is the implement option.
  - Evidence: `pytest tests/go-cmd/test_orchestrator_lifecycle_menu.py::TestWipIdeaMenu tests/go-cmd/test_orchestrator_default_selection.py -v` passes with new/updated tests
  - Steps:
    - [x] In `tests/go-cmd/test_orchestrator_lifecycle_menu.py`, change `TestWipIdeaMenu.test_wip_idea_no_config_defaults_to_configure` to `test_wip_idea_no_changes_defaults_to_implement` — assert default is the implement label (matches `"Implement the entire plan"`).
    - [x] Add `test_wip_idea_with_uncommitted_changes_defaults_to_commit` in `TestWipIdeaMenu` — assert default is `COMMIT_CHANGES` when git is dirty.
    - [x] In `_lifecycle_default()`, add the `"wip"` case: if `COMMIT_CHANGES` is in options, return its index; otherwise return the index of the implement option.
    - [x] Update `tests/go-cmd/test_orchestrator_default_selection.py` — the existing tests use `_wip_project()` which has no metadata file. These tests now exercise the "no metadata / unknown state" fallback (Task 1.4). Review and adjust assertions:
      - `test_no_config_defaults_to_configure` — still valid (no metadata → falls back to option 2)
      - `test_config_exists_with_uncommitted_changes_defaults_to_commit` — will now default to option 2 (configure/revise) since no metadata means fallback. Update this test to use a lifecycle project in `wip` state, or add a separate test. If keeping the no-metadata test, change expected default to `REVISE_IMPLEMENT`.
      - `test_config_exists_no_changes_defaults_to_revise` — still valid (no metadata → option 2 is revise implement)
    - [x] Run all go-cmd tests.

### Task 1.4: Missing/unknown metadata falls back to option 2

- [x] **Task 1.4: Missing or unknown metadata state falls back to option 2**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <idea-without-metadata>` (menu presentation)
  - Observable: When metadata file is missing or has unknown state, default is option 2 (Configure/Revise implement options)
  - Evidence: `pytest tests/go-cmd/test_orchestrator_default_selection.py -v` passes with tests for no-metadata and unknown-state scenarios
  - Steps:
    - [x] Ensure `tests/go-cmd/test_orchestrator_default_selection.py` has a test for no-metadata fallback (the existing `test_no_config_defaults_to_configure` already covers this with `_wip_project` which has no metadata).
    - [x] Add a test with metadata containing an unrecognized state (e.g., `state: archived`) — assert default is option 2 (configure/revise).
    - [x] Verify `_lifecycle_default()` handles `None` state and unknown states by falling back to `return 2`.
    - [x] Run all go-cmd tests to confirm no regressions.

## Steel Thread 2: Optimize Metadata Reading

- [x] **Task 2.1: Read metadata once per menu build instead of twice**
  - TaskType: REFACTOR
  - Entrypoint: `pytest tests/go-cmd/ -v`
  - Observable: No behavior change — all existing tests pass
  - Evidence: `pytest tests/go-cmd/ -v` passes with zero failures
  - Steps:
    - [x] In `_build_has_plan_options()`, call `_read_lifecycle_state()` once and store the result.
    - [x] Pass the state to `_lifecycle_move_label()` (rename or add parameter) so it does not re-read the metadata file.
    - [x] Pass the state to `_lifecycle_default()` so it does not re-read the metadata file.
    - [x] Remove the metadata reading from `_lifecycle_move_label()` — it should now accept state as a parameter and just do the dict lookup.
    - [x] Run all go-cmd tests to confirm no regressions.

---

## Change History
### 2026-03-14 16:17 - mark-step-complete
Renamed test method

### 2026-03-14 16:17 - mark-step-complete
Added test_ready_idea_with_config_defaults_to_revise

### 2026-03-14 16:17 - mark-step-complete
Added ready case in _lifecycle_default

### 2026-03-14 16:17 - mark-step-complete
All 199 tests pass

### 2026-03-14 16:18 - mark-task-complete
Ready state defaults to configure/revise implement options

### 2026-03-14 16:23 - mark-step-complete
Renamed test to test_wip_idea_no_changes_defaults_to_implement, asserts default starts with IMPLEMENT_PLAN

### 2026-03-14 16:23 - mark-step-complete
Added test_wip_idea_with_uncommitted_changes_defaults_to_commit

### 2026-03-14 16:23 - mark-step-complete
Added wip case in _lifecycle_default and _implement_option_index helper

### 2026-03-14 16:23 - mark-step-complete
Existing tests in test_orchestrator_default_selection.py pass as-is - they exercise the no-metadata fallback

### 2026-03-14 16:23 - mark-step-complete
All 200 go-cmd tests pass

### 2026-03-14 16:24 - mark-task-complete
WIP state defaults to implement when clean, commit when dirty

### 2026-03-14 16:28 - mark-task-complete
Added test for unknown state fallback; verified existing implementation handles None and unknown states correctly

### 2026-03-14 16:33 - mark-task-complete
Refactored to read metadata once per menu build
