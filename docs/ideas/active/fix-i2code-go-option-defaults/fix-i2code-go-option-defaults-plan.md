
# Plan: Fix i2code go menu default selection logic

## Idea Type

**A. User-facing feature** (bug fix in a user-facing CLI feature)

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

## Key Files

| File | Role |
|------|------|
| `src/i2code/go_cmd/orchestrator.py` | Production code: `_read_lifecycle_state()` (line 298), `_lifecycle_default()` (line 332), `_build_has_plan_options()` (line 313) |
| `src/i2code/idea/metadata.py` | `read_metadata()` and `write_metadata()` helper functions |
| `tests/go-cmd/test_orchestrator_lifecycle_menu.py` | Lifecycle menu tests (draft, ready, wip state defaults) |
| `tests/go-cmd/test_orchestrator_default_selection.py` | Default selection tests for projects without lifecycle metadata |

## Steel Thread 1: Auto-create metadata for projects entering the go workflow

Projects created outside `i2code go` (e.g., via `i2code idea`/`i2code spec`/`i2code plan`) have no metadata file. Without metadata, `_read_lifecycle_state()` returns `None`, lifecycle move options don't appear, and the fallback default picks the wrong option. This thread adds auto-creation of metadata with `state: draft`.

- [ ] **Task 1.1: Auto-create metadata file with state draft when no metadata exists in HAS_PLAN**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/go-cmd/test_orchestrator_lifecycle_menu.py -x`
  - Observable: When `_read_lifecycle_state()` encounters a project in HAS_PLAN state (idea, spec, plan files exist) with no metadata file, it creates metadata with `state: draft` and returns `"draft"`. The menu then shows "Move idea to ready" and defaults to it. When metadata already exists, it is NOT overwritten.
  - Evidence: New tests in `tests/go-cmd/test_orchestrator_lifecycle_menu.py` verify: (1) a project without metadata gets auto-created metadata and defaults to MOVE_TO_READY, (2) a project with existing metadata is not overwritten.
  - Steps:
    - [ ] Add a new test class `TestAutoCreateMetadata` in `tests/go-cmd/test_orchestrator_lifecycle_menu.py` with two tests:
      - `test_no_metadata_auto_creates_draft_and_defaults_to_move_to_ready` — creates a project with plan files but no metadata file, runs orchestrator, asserts default is MOVE_TO_READY and metadata file now exists with `state: draft`
      - `test_existing_metadata_not_overwritten` — creates a project with metadata `state: ready`, runs orchestrator, asserts metadata still contains `state: ready`
    - [ ] Modify `_read_lifecycle_state()` in `src/i2code/go_cmd/orchestrator.py:298` to auto-create metadata when the metadata file does not exist: call `write_metadata(metadata_path, {"state": "draft"})` and return `"draft"`. Import `write_metadata` from `i2code.idea.metadata`
    - [ ] Run tests and verify both new tests pass and all existing tests still pass

## Steel Thread 2: Fix ready-state default to advance workflow when config exists

When the implement config file already exists and the project is in `ready` state, the default is "Revise implement options" instead of "Move idea to wip". The user should advance through the workflow, not revisit already-completed configuration.

- [ ] **Task 2.1: Ready state with existing config defaults to MOVE_TO_WIP**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/go-cmd/test_orchestrator_lifecycle_menu.py::TestReadyIdeaMenu -x`
  - Observable: When lifecycle state is `"ready"` and the implement config file exists, the menu default is "Move idea to wip" instead of "Revise implement options".
  - Evidence: `test_ready_idea_with_config_defaults_to_revise` in `tests/go-cmd/test_orchestrator_lifecycle_menu.py:167` is updated to expect `MOVE_TO_WIP` and passes.
  - Steps:
    - [ ] Update `test_ready_idea_with_config_defaults_to_revise` in `tests/go-cmd/test_orchestrator_lifecycle_menu.py:167`: change expected default from `REVISE_IMPLEMENT` to `MOVE_TO_WIP`, and rename to `test_ready_idea_with_config_defaults_to_move_to_wip`
    - [ ] Run the test — verify it fails (current code returns REVISE_IMPLEMENT)
    - [ ] Modify `_lifecycle_default()` in `src/i2code/go_cmd/orchestrator.py:332`: for `state == "ready"`, check if config file exists (`os.path.isfile(self._project.implement_config_file)`). If config exists and `MOVE_TO_WIP` is in options, return `options.index(MOVE_TO_WIP) + 1`. Otherwise, return the configure label index as before.
    - [ ] Run all tests in `tests/go-cmd/test_orchestrator_lifecycle_menu.py` — verify all pass

## Steel Thread 3: Fix fallback default for unknown lifecycle state

After Steel Thread 1, the `None`-state fallback in `_lifecycle_default()` (lines 342-344) is mostly unreachable for HAS_PLAN projects, but projects in `wip/` directories without metadata (used in `test_orchestrator_default_selection.py`) still hit it. The fallback should use configure → commit → implement priority.

- [ ] **Task 3.1: Fallback default prefers configure over commit when no config exists**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/go-cmd/test_orchestrator_default_selection.py -x`
  - Observable: When lifecycle state is unknown/None, config file exists, and working tree is clean, the fallback default is the configure/revise label (not COMMIT_CHANGES, not option index 2).
  - Evidence: `test_config_exists_no_changes_defaults_to_revise` in `tests/go-cmd/test_orchestrator_default_selection.py:108` continues to pass (fallback picks the configure/revise label). All other tests in this file pass.
  - Steps:
    - [ ] Review current fallback logic in `src/i2code/go_cmd/orchestrator.py:342-344` and the test expectations in `tests/go-cmd/test_orchestrator_default_selection.py`
    - [ ] Verify all tests in `tests/go-cmd/test_orchestrator_default_selection.py` pass with the changes from Steel Threads 1 and 2. The `_wip_project()` helper creates projects in a `wip/` directory path — confirm whether auto-creation fires or not for these projects and adjust if needed
    - [ ] If the fallback logic needs adjustment to maintain correct defaults for unknown-state projects, update the fallback in `_lifecycle_default()` to follow configure → commit → implement priority: first check for the configure label, then COMMIT_CHANGES, then implement
    - [ ] Run the full test suite: `pytest tests/go-cmd/test_orchestrator_default_selection.py tests/go-cmd/test_orchestrator_lifecycle_menu.py -x` — verify all tests pass
