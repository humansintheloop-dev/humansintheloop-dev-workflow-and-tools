# Implementation Plan: Maintain Idea State in Metadata File

## Idea Type

**C. Platform/infrastructure capability** — This refactors the internal idea lifecycle management system from directory-based state to metadata-file-based state.

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `pytest`), its exit code, and the last 20 lines of output

---

## Key File Paths

| Component | Path |
|-----------|------|
| Idea resolver | `src/i2code/idea/resolver.py` |
| State CLI command | `src/i2code/idea_cmd/state_cmd.py` |
| Transition rules | `src/i2code/idea_cmd/transition_rules.py` |
| List CLI command | `src/i2code/idea_cmd/list_cmd.py` |
| Brainstorm command | `src/i2code/idea_cmd/brainstorm.py` |
| Idea CLI group | `src/i2code/idea_cmd/cli.py` |
| IdeaProject | `src/i2code/implement/idea_project.py` |
| State tests | `tests/idea-cmd/test_idea_state_cli.py` |
| Project deps | `pyproject.toml` |
| Write-idea skill | `skills/write-idea/SKILL.md` |
| CI workflow | `.github/workflows/ci.yml` |

---

## Steel Thread 1: Metadata File I/O and Resolver Refactoring

This steel thread establishes the core infrastructure: metadata YAML read/write, the new `active/`/`archived/` directory scanning, and the updated resolver. All subsequent threads depend on this foundation.

- [x] **Task 1.1: Metadata file read/write module**
  - TaskType: INFRA
  - Entrypoint: `pytest tests/idea-cmd/test_metadata.py`
  - Observable: A `read_metadata(path)` function reads a YAML metadata file and returns a dict with at least `state`; a `write_metadata(path, data)` function writes/updates YAML preserving unknown keys; reading a non-existent file raises a clear error
  - Evidence: `pytest tests/idea-cmd/test_metadata.py` passes with tests covering read, write, round-trip with unknown keys, and missing-file error
  - Steps:
    - [x] Add `PyYAML` to `dependencies` in `pyproject.toml`
    - [x] Create test file `tests/idea-cmd/test_metadata.py` with tests for: reading a valid metadata file returns `{"state": "draft"}`; writing then reading round-trips correctly; unknown keys in YAML are preserved on write; reading a missing file raises `FileNotFoundError`
    - [x] Create `src/i2code/idea/metadata.py` with `read_metadata(path: Path) -> dict` and `write_metadata(path: Path, data: dict) -> None` using `yaml.safe_load()` and `yaml.safe_dump()`

- [x] **Task 1.2: Resolver scans active/ and archived/ directories and reads state from metadata files**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_resolver.py`
  - Observable: `resolve_idea(name, git_root)` finds an idea in `docs/ideas/active/` or `docs/ideas/archived/` and returns `IdeaInfo` with `state` read from the metadata file; `list_ideas(git_root)` scans `active/` (and optionally `archived/`) and returns `IdeaInfo` list with states from metadata files; `state_from_path()` is removed
  - Evidence: `pytest tests/idea-cmd/test_resolver.py` passes with tests covering: resolve from active, resolve from archived, list active only, list with archived, idea not found error, missing metadata file warning
  - Steps:
    - [x] Create `tests/idea-cmd/test_resolver.py` with tests for the new resolver behavior: resolving an idea in `active/`, resolving in `archived/`, listing active ideas only, listing all ideas, handling missing metadata files
    - [x] Update `src/i2code/idea/resolver.py`: change `resolve_idea()` to scan `docs/ideas/active/` and `docs/ideas/archived/` instead of 5 state directories; read state from `<name>-metadata.yaml` instead of using `state_from_path()`
    - [x] Update `list_ideas()` to accept an optional `include_archived: bool = False` parameter; scan `active/` by default, add `archived/` when `include_archived=True`
    - [x] Remove or deprecate `state_from_path()` function
    - [x] Keep `LIFECYCLE_STATES` and `IdeaInfo` unchanged

- [x] **Task 1.3: IdeaProject gains metadata_file property**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_idea_project_metadata.py`
  - Observable: `IdeaProject.metadata_file` returns the path `<directory>/<name>-metadata.yaml`
  - Evidence: `pytest tests/idea-cmd/test_idea_project_metadata.py` passes
  - Steps:
    - [x] Create test in `tests/idea-cmd/test_idea_project_metadata.py` asserting `metadata_file` returns correct path
    - [x] Add `metadata_file` property to `src/i2code/implement/idea_project.py` returning `os.path.join(self.directory, f"{self.name}-metadata.yaml")`

---

## Steel Thread 2: State Transitions via Metadata File

Implements Scenario 1 (primary) and Scenario 6 (forced backward transition). State transitions now edit the metadata file instead of using `git mv`.

- [x] **Task 2.1: State query reads from metadata file**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_idea_state_cli.py::TestIdeaStateQuery`
  - Observable: `i2code idea state my-feature` returns the state read from `my-feature-metadata.yaml`, not from the directory path
  - Evidence: `pytest tests/idea-cmd/test_idea_state_cli.py::TestIdeaStateQuery` passes with ideas in `active/` directory structure
  - Steps:
    - [x] Update test fixtures in `tests/idea-cmd/test_idea_state_cli.py` to create ideas in `docs/ideas/active/<name>/` with `<name>-metadata.yaml` instead of `docs/ideas/<state>/<name>/`
    - [x] Create `TestIdeaStateQuery` test class (replacing `TestIdeaStateByName` and `TestIdeaStateByPath`) that verifies state is read from metadata file
    - [x] Update `src/i2code/idea_cmd/state_cmd.py` to use the refactored resolver (which reads metadata files) for state queries

- [x] **Task 2.2: State transitions edit metadata file instead of moving directories**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_idea_state_cli.py::TestStateTransition`
  - Observable: `i2code idea state my-feature ready` writes `state: ready` to the metadata file, commits, and the idea directory does NOT move; `git log --name-only` shows only the metadata file changed
  - Evidence: `pytest tests/idea-cmd/test_idea_state_cli.py::TestStateTransition` passes, asserting metadata file content changed and directory path is unchanged
  - Steps:
    - [x] Create `TestStateTransition` test class verifying: metadata file updated to new state, directory not moved, git commit message is correct, git log shows only metadata file changed
    - [x] Rewrite `execute_transition()` in `src/i2code/idea_cmd/state_cmd.py` to: read metadata, write new state to metadata file, `git add` metadata file, `git commit`
    - [x] Remove directory-moving logic (`git mv`) from `execute_transition()`

- [x] **Task 2.3: --no-commit flag for state transitions**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_idea_state_cli.py::TestStateTransitionNoCommit`
  - Observable: `i2code idea state my-feature ready --no-commit` updates the metadata file and stages it but does not create a git commit
  - Evidence: `pytest tests/idea-cmd/test_idea_state_cli.py::TestStateTransitionNoCommit` passes, asserting metadata file is staged but no new commit exists
  - Steps:
    - [x] Add `--no-commit` option to state command in `src/i2code/idea_cmd/state_cmd.py`
    - [x] Create `TestStateTransitionNoCommit` test verifying file is staged but not committed
    - [x] Update `execute_transition()` to skip commit when `--no-commit` is passed

- [x] **Task 2.4: Existing transition rules work with metadata-based state**
  - TaskType: OUTCOME
  - Entrypoint: `pytest tests/idea-cmd/test_idea_state_cli.py -k "transition_rule or force"`
  - Observable: Forward-only progression, plan-file requirements, always-allowed abandoned transitions, skip-blocking, and `--force` override all work identically to the current behavior but reading/writing state via metadata files
  - Evidence: `pytest tests/idea-cmd/test_idea_state_cli.py -k "transition_rule or force"` passes
  - Steps:
    - [x] Update `TestTransitionRuleForwardOnly`, `TestTransitionRulePlanRequired`, `TestTransitionRuleAlwaysAllowed`, `TestTransitionRuleSkipBlocked`, and `TestTransitionForceOverride` test classes to use `active/` directory structure with metadata files
    - [x] Verify `src/i2code/idea_cmd/transition_rules.py` `validate_transition()` still works correctly — it should be state-based and unchanged; confirm that plan-file checks still reference the correct directory

---

## Steel Thread 3: Migration from Directory-Based State

Implements Scenario 2. Provides a permanent `migrate` command for moving from the old 5-directory structure to the new metadata-based structure.

- [x] **Task 3.1: Migrate command moves ideas to active/ with metadata files**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea migrate`
  - Observable: All ideas from `docs/ideas/{draft,ready,wip,completed,abandoned}/` are moved to `docs/ideas/active/` with correct `<name>-metadata.yaml` files; old state directories are removed; a single git commit is created with message "Migrate ideas from directory-based state to metadata files"
  - Evidence: `pytest tests/idea-cmd/test_migrate.py` passes with tests verifying: ideas moved to `active/`, metadata files contain correct state, old directories removed, single commit created
  - Steps:
    - [x] Create `tests/idea-cmd/test_migrate.py` with tests: migrate 2+ ideas from different state dirs, verify metadata files, verify old dirs removed, verify single commit
    - [x] Create `src/i2code/idea_cmd/migrate_cmd.py` with migrate command implementation
    - [x] Register `migrate` subcommand in `src/i2code/idea_cmd/cli.py`

- [x] **Task 3.2: Migration is idempotent and supports --no-commit**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea migrate`
  - Observable: Running `migrate` when no old-style directories exist prints "No ideas to migrate" and exits 0; `--no-commit` flag stages changes without committing
  - Evidence: `pytest tests/idea-cmd/test_migrate.py::TestMigrateIdempotent` and `pytest tests/idea-cmd/test_migrate.py::TestMigrateNoCommit` pass
  - Steps:
    - [x] Add `TestMigrateIdempotent` test: run migrate twice, second run prints message and exits cleanly
    - [x] Add `TestMigrateNoCommit` test: `--no-commit` stages files but does not create commit
    - [x] Implement idempotency check and `--no-commit` flag in `src/i2code/idea_cmd/migrate_cmd.py`

---

## Steel Thread 4: Archive and Unarchive

Implements Scenario 3. Archive moves an idea from `active/` to `archived/` via `git mv`; unarchive reverses it.

- [x] **Task 4.1: Archive command moves idea from active/ to archived/**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea archive old-feature`
  - Observable: Idea directory moves from `docs/ideas/active/old-feature/` to `docs/ideas/archived/old-feature/`; git commit with message "Archive idea old-feature"; lifecycle state in metadata file is unchanged; error if idea already archived
  - Evidence: `pytest tests/idea-cmd/test_archive.py::TestArchive` passes
  - Steps:
    - [x] Create `tests/idea-cmd/test_archive.py` with `TestArchive` class: archive moves directory, commit message correct, metadata state preserved, error on already-archived idea
    - [x] Create `src/i2code/idea_cmd/archive_cmd.py` with `archive` command
    - [x] Register `archive` subcommand in `src/i2code/idea_cmd/cli.py`
    - [x] Support `--no-commit` flag

- [x] **Task 4.2: Unarchive command moves idea from archived/ to active/**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea unarchive old-feature`
  - Observable: Idea directory moves from `docs/ideas/archived/old-feature/` to `docs/ideas/active/old-feature/`; git commit with message "Unarchive idea old-feature"; lifecycle state unchanged; error if idea already in active
  - Evidence: `pytest tests/idea-cmd/test_archive.py::TestUnarchive` passes
  - Steps:
    - [x] Add `TestUnarchive` class to `tests/idea-cmd/test_archive.py`: unarchive moves directory, commit message correct, metadata state preserved, error on already-active idea
    - [x] Add `unarchive` command to `src/i2code/idea_cmd/archive_cmd.py`
    - [x] Register `unarchive` subcommand in `src/i2code/idea_cmd/cli.py`
    - [x] Support `--no-commit` flag

- [x] **Task 4.3: Archive/unarchive round-trip preserves state**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea archive my-idea && i2code idea unarchive my-idea`
  - Observable: After archive then unarchive, the idea is back in `active/` with its lifecycle state unchanged
  - Evidence: `pytest tests/idea-cmd/test_archive.py::TestArchiveRoundTrip` passes
  - Steps:
    - [x] Add `TestArchiveRoundTrip` test: create idea with `state: wip`, archive, unarchive, assert directory is in `active/` and metadata state is still `wip`

---

## Steel Thread 5: Listing with Archive Filters

Implements Scenario 5. Adds `--archived` and `--all` flags to the list command.

- [ ] **Task 5.1: List command shows active ideas by default and supports --archived and --all flags**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea list`
  - Observable: `i2code idea list` shows only active ideas; `--archived` shows only archived ideas; `--all` shows both; `--state` filter works with all three modes; `--archived` and `--all` are mutually exclusive
  - Evidence: `pytest tests/idea-cmd/test_list_cmd.py` passes with tests for each flag combination
  - Steps:
    - [ ] Create `tests/idea-cmd/test_list_cmd.py` with tests: list defaults to active only; `--state wip` filters active by state; `--archived` shows archived only; `--all` shows both; `--archived --state completed` filters archived by state; `--archived` and `--all` are mutually exclusive (error)
    - [ ] Update `src/i2code/idea_cmd/list_cmd.py` to add `--archived` and `--all` click options
    - [ ] Pass appropriate `include_archived` parameter to `list_ideas()` based on flags
    - [ ] Filter results by `--state` when provided

---

## Steel Thread 6: Idea Creation with Metadata

Implements Scenario 4. New ideas are created in `active/` with a metadata file.

- [ ] **Task 6.1: Brainstorm creates ideas in active/ with metadata file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea brainstorm docs/ideas/active/new-idea`
  - Observable: Idea directory created at `docs/ideas/active/new-idea/` with `new-idea-metadata.yaml` containing `state: draft` and `new-idea-idea.md` with template text
  - Evidence: `pytest tests/idea-cmd/test_brainstorm.py` passes verifying directory location, metadata file exists with `state: draft`
  - Steps:
    - [ ] Create or update `tests/idea-cmd/test_brainstorm.py` with test verifying brainstorm creates idea in `active/` with metadata file
    - [ ] Update `src/i2code/idea_cmd/brainstorm.py` to create idea directory under `docs/ideas/active/` and write `<name>-metadata.yaml` with `state: draft`

- [ ] **Task 6.2: Update write-idea skill to use active/ directory with metadata**
  - TaskType: OUTCOME
  - Entrypoint: Review `skills/write-idea/SKILL.md`
  - Observable: The write-idea skill instructs Claude to create ideas in `docs/ideas/active/<name>/` and create `<name>-metadata.yaml` with `state: draft`
  - Evidence: `skills/write-idea/SKILL.md` references `docs/ideas/active/` and includes metadata file creation instruction
  - Steps:
    - [ ] Update `skills/write-idea/SKILL.md`: change directory path from `docs/ideas/draft/<name>/` to `docs/ideas/active/<name>/`; add step to create `<name>-metadata.yaml` with `state: draft`

---

## Steel Thread 7: Documentation and Cleanup

- [ ] **Task 7.1: Update CODEBASE.md to reflect new directory structure**
  - TaskType: INFRA
  - Entrypoint: `cat CODEBASE.md`
  - Observable: `CODEBASE.md` documents the new `docs/ideas/active/` and `docs/ideas/archived/` directory structure, the metadata file convention, and the new CLI commands (`archive`, `unarchive`, `migrate`)
  - Evidence: `CODEBASE.md` contains sections describing the new structure; `grep -c "active/" CODEBASE.md` returns matches
  - Steps:
    - [ ] Update `CODEBASE.md` to replace references to 5-directory layout with 2-directory layout (`active/`, `archived/`)
    - [ ] Document the `<name>-metadata.yaml` file convention
    - [ ] Add `archive`, `unarchive`, `migrate` to CLI command reference

- [ ] **Task 7.2: Remove dead code and ensure all tests pass**
  - TaskType: REFACTOR
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: No behavior change; all dead code from directory-based state management is removed; all tests pass
  - Evidence: `./test-scripts/test-end-to-end.sh` exits 0
  - Steps:
    - [ ] Remove `state_from_path()` from `src/i2code/idea/resolver.py` if not already removed
    - [ ] Remove any remaining `git mv` directory-moving logic from `src/i2code/idea_cmd/state_cmd.py`
    - [ ] Run full test suite and fix any remaining failures
    - [ ] Run `uvx pyright --level error src/` and fix type errors

---

## Change History
### 2026-03-11 08:58 - mark-step-complete
TestStateTransition test class created with 4 tests verifying metadata file update, no directory move, commit message, and only metadata file changed

### 2026-03-11 08:58 - mark-step-complete
Rewrote execute_transition() to read/write metadata file and git add instead of git mv

### 2026-03-11 08:58 - mark-step-complete
git mv directory-moving logic replaced with metadata file write + git add

### 2026-03-11 08:58 - mark-task-complete
State transitions now edit metadata file instead of moving directories

### 2026-03-11 09:10 - mark-step-complete
Tests already use _committed_active_idea with metadata files from prior task updates

### 2026-03-11 09:10 - mark-step-complete
validate_transition() is state-based, _has_plan uses idea_dir.glob which works with active/ directory

### 2026-03-11 09:10 - mark-task-complete
All 12 transition rule and force tests pass with metadata-based state

### 2026-03-11 09:30 - mark-task-complete
Added TestMigrateIdempotent and TestMigrateNoCommit test classes; implementation already existed from task 3.1

### 2026-03-11 09:43 - mark-step-complete
Added TestUnarchive class with 5 tests: moves directory, commit message, preserves metadata, error on already-active, no-commit flag

### 2026-03-11 09:43 - mark-step-complete
Added idea_unarchive command to archive_cmd.py

### 2026-03-11 09:43 - mark-step-complete
Registered idea_unarchive in cli.py

### 2026-03-11 09:43 - mark-step-complete
Unarchive command supports --no-commit flag

### 2026-03-11 09:43 - mark-task-complete
Unarchive command implemented with all 5 tests passing
