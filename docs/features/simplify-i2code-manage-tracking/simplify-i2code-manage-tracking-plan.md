Now I have a complete understanding of the codebase. Here's the plan:

---

# Plan: Simplify i2code manage-tracking

## Idea Type

**A. User-facing feature** — Renames and simplifies an existing CLI command, and adds subdirectory `.hitl/` consolidation behavior.

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

## Overview

This plan restructures the `i2code manage-tracking` CLI command into `i2code tracking setup`, makes migration the default behavior (removing the `--migrate` flag), extends subdirectory consolidation to handle `.hitl/` directories, and adds error handling for link conflicts.

### Current state

- **CLI command**: `src/i2code/tracking/cli.py` defines `manage_tracking_cmd` as a flat Click command requiring `--migrate` and/or `--link DIR`
- **Business logic**: `src/i2code/tracking/manage.py` contains `TrackingManager` class with `migrate()` and `link()` public functions
- **Tests**: `tests/tracking/test_manage.py` has 19 unit tests covering migrate, link, and combined scenarios
- **Smoke tests**: `test-scripts/test-subcommands-smoke.sh` does NOT currently test `manage-tracking`
- **Documentation**: `docs/i2code-cli/manage-tracking.adoc`, `docs/i2code-cli/i2code-cli.adoc`, `README.adoc`
- **CI**: `.github/workflows/ci.yml` runs `./test-scripts/test-end-to-end.sh` which includes unit tests and smoke tests
- **Key limitation**: `_find_subdirectory_claude_dirs()` in `manage.py:309-315` explicitly skips `.hitl` directories during `os.walk`, so subdirectory `.hitl/` real directories are never consolidated

### Key files

| File | Role |
|------|------|
| `src/i2code/tracking/cli.py` | Click command definition (will change from flat command to group+subcommand) |
| `src/i2code/tracking/manage.py` | `TrackingManager` business logic (will gain `.hitl/` subdirectory consolidation) |
| `src/i2code/cli.py` | Top-level CLI group registration (will import tracking group instead of flat command) |
| `tests/tracking/test_manage.py` | Unit tests for migrate/link behavior |
| `test-scripts/test-subcommands-smoke.sh` | CLI discoverability smoke tests |
| `docs/i2code-cli/manage-tracking.adoc` | Command documentation (will be renamed to `tracking.adoc`) |
| `docs/i2code-cli/i2code-cli.adoc` | CLI reference page |
| `README.adoc` | Project README |

All steps should be implemented using TDD.

---

## Steel Thread 1: Domain model + `i2code tracking setup` replaces `manage-tracking` with default migration
This thread introduces the TrackedWorkingDirectory domain model and restructures the CLI from `i2code manage-tracking --migrate [--link DIR]` to `i2code tracking setup [--link DIR]`. The model follows a scan-then-act pattern: scan the filesystem to build a tree of TrackedDirectory instances (each with optional LegacyTracking and HitlTracking sub-elements containing TrackingDir instances for sessions and issues), then act on the tree to transition every node to the target state (HitlTracking only). Migration always runs (no `--migrate` flag). The old `manage-tracking` command is removed entirely.

- [x] **Task 1.1: Domain model classes: TrackingDir, LegacyTracking, HitlTracking, TrackedDirectory, TrackedWorkingDirectory**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/tracking/`
  - Observable: Domain model classes exist with full behavior: TrackingDir wraps a path with exists/is_symlink/symlink_target/list_files/migrate_to methods; LegacyTracking and HitlTracking each contain sessions and issues TrackingDir instances; TrackedDirectory has optional LegacyTracking and optional HitlTracking with status derived from which sub-elements exist; TrackedWorkingDirectory contains a root TrackedDirectory and scans filesystem to discover child TrackedDirectory instances
  - Evidence: `./test-scripts/test-end-to-end.sh passes — unit tests verify TrackingDir behavior, LegacyTracking/HitlTracking composition, TrackedDirectory derived status, and TrackedWorkingDirectory filesystem scanning`
  - Steps:
    - [x] Create `src/i2code/tracking/model.py` with TrackingDir class: wraps a Path, provides exists, is_symlink, symlink_target, list_files, migrate_to(target) methods — TDD with unit tests
    - [x] Add LegacyTracking and HitlTracking classes to model.py: each contains sessions and issues TrackingDir instances, constructed from a base path (.claude or .hitl) — TDD
    - [x] Add TrackedDirectory class to model.py: has optional LegacyTracking and optional HitlTracking, status derived from which sub-elements exist — TDD
    - [x] Add TrackedWorkingDirectory class to model.py: contains root TrackedDirectory, scans filesystem to discover child TrackedDirectory instances in subdirectories — TDD
- [x] **Task 1.2: `i2code tracking setup` performs root migration by default and `manage-tracking` is removed**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code tracking setup`
  - Observable: `i2code tracking setup` creates .hitl/{sessions,issues} and updates .gitignore; migrates .claude/{sessions,issues} to .hitl/{sessions,issues} if present; `i2code tracking setup --dry-run` previews changes; `manage-tracking` is NOT listed in `i2code --help`; `tracking` group with `setup` subcommand IS listed
  - Evidence: `./test-scripts/test-end-to-end.sh passes — existing unit tests for migrate/link behavior updated to use new model, smoke tests verify CLI discoverability of `tracking setup` and absence of `manage-tracking``
  - Steps:
    - [x] Rewrite `src/i2code/tracking/cli.py`: create `tracking` Click group with `setup` subcommand; setup builds TrackedWorkingDirectory from cwd, then acts on it to transition root to target state; always migrates (no --migrate flag); preserve --link DIR and --dry-run flags
    - [x] Update `src/i2code/cli.py`: import and register the `tracking` group instead of `manage_tracking_cmd`
    - [x] Refactor `src/i2code/tracking/manage.py`: replace TrackingManager procedural logic with functions that operate on TrackedWorkingDirectory domain model
    - [x] Add smoke tests to `test-scripts/test-subcommands-smoke.sh`: verify `tracking` is listed in `i2code --help`, `setup` is listed in `i2code tracking --help`, `tracking setup --help` exits 0, and `manage-tracking` is NOT listed in `i2code --help`
    - [x] Rename `docs/i2code-cli/manage-tracking.adoc` to `docs/i2code-cli/tracking.adoc` using `git mv`; update content to reflect new command and domain model
    - [x] Update `docs/i2code-cli/i2code-cli.adoc` and `README.adoc`: change `manage-tracking` references to `tracking setup`
## Steel Thread 2: Subdirectory children consolidated into top-level
When `i2code tracking setup` runs and subdirectories contain real `.claude/` or `.hitl/` tracking directories, the TrackedWorkingDirectory model discovers them as child TrackedDirectory instances. Each child is transitioned to the target state: contents merged into the root `.hitl/{sessions,issues}` and replaced with relative symlinks. LegacyLinked children (existing symlinks) have their symlinks replaced to point to the parent `.hitl/`.

- [ ] **Task 2.1: Subdirectory children with .claude or .hitl real directories are consolidated into root and replaced with symlinks**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code tracking setup (run in a project where subdirectories have real .claude/ or .hitl/ tracking directories)`
  - Observable: Child TrackedDirectory instances with LegacyTracking or HitlTracking real directories have their contents merged into root .hitl/{sessions,issues}; subdirectory tracking dirs are replaced with relative symlinks pointing to the top-level; LegacyLinked children (existing symlinks) have their symlinks replaced to point to parent .hitl; existing correct symlinks are skipped; running twice is idempotent
  - Evidence: `./test-scripts/test-end-to-end.sh passes — unit tests verify child TrackedDirectory consolidation for all child states (LegacyTracking real dirs, LegacyTracking symlinks, HitlTracking real dirs), including merge, symlink creation, already-correct skip, dry-run skip, multiple subdirectories, and filename conflict behavior`
  - Steps:
    - [ ] Extend TrackedWorkingDirectory scanning to discover child TrackedDirectory instances with LegacyTracking and/or HitlTracking in subdirectories — TDD
    - [ ] Add consolidation action for children with LegacyTracking real dirs: migrate contents to root HitlTracking, replace with relative symlinks to root .hitl — TDD
    - [ ] Add consolidation action for children with HitlTracking real dirs: merge contents to root HitlTracking, replace with relative symlinks to root .hitl — TDD
    - [ ] Handle LegacyLinked children: replace existing symlinks to point to parent .hitl rather than moving files — TDD
    - [ ] Add unit tests for edge cases: already-correct symlink skip, dry-run skip, multiple subdirectories, filename conflict keeps root version
## Steel Thread 3: `--link` rejects conflicting symlinks
When `--link DIR` is specified and the root HitlTracking sessions/issues TrackingDir instances are already symlinks pointing to a DIFFERENT directory than `DIR`, the command raises an error and makes no changes. This uses the TrackingDir.symlink_target property to detect conflicts before any mutations.

- [ ] **Task 3.1: `--link DIR` raises error when root HitlTracking symlinks point to a different directory**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code tracking setup --link /new/path (when .hitl/{sessions,issues} are symlinked to /old/path)`
  - Observable: Error message indicating the existing symlinks point to a different directory; exit code is non-zero; no changes are made to the filesystem
  - Evidence: `./test-scripts/test-end-to-end.sh passes — updated unit test verifies error is raised for conflicting symlinks; new test verifies no filesystem modifications occur on conflict`
  - Steps:
    - [ ] Add link conflict detection: when root HitlTracking sessions/issues TrackingDir instances are symlinks pointing to a different target than the requested --link DIR, raise click.ClickException — TDD
    - [ ] Update existing `test_replaces_incorrect_symlink` to assert error is raised instead of silent replacement
    - [ ] Add `test_link_conflict_makes_no_changes` to verify no filesystem modifications occur when conflict detected
## Change History

| Date | Change | Rationale |
|------|--------|-----------|

### 2026-02-22 10:01 - replace-thread
Introduce TrackedWorkingDirectory domain model with scan-then-act pattern; split into model classes task and CLI wiring task

### 2026-02-22 10:01 - replace-thread
Updated to use TrackedWorkingDirectory domain model for child discovery and consolidation

### 2026-02-22 10:01 - replace-thread
Updated to use TrackingDir domain model for conflict detection

### 2026-02-22 11:44 - mark-step-complete
TrackingDir class implemented with TDD: 13 tests for exists, is_symlink, symlink_target, list_files, migrate_to, path

### 2026-02-22 11:44 - mark-step-complete
LegacyTracking and HitlTracking classes implemented with TDD: 6 tests for sessions/issues TrackingDir composition

### 2026-02-22 11:44 - mark-step-complete
TrackedDirectory class implemented with TDD: 12 tests for from_path detection, status derivation, path attribute

### 2026-02-22 11:44 - mark-step-complete
TrackedWorkingDirectory class implemented with TDD: 9 tests for scan, child discovery, skip dirs, nested paths

### 2026-02-22 11:44 - mark-task-complete
All domain model classes implemented with TDD: TrackingDir, LegacyTracking, HitlTracking, TrackedDirectory, TrackedWorkingDirectory — 40 tests pass
