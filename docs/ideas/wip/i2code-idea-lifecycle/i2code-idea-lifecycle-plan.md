Now I have all skill guidance loaded. Let me generate the plan.

---

# i2code Idea Lifecycle — Implementation Plan

## Idea Type

**Type A: User-facing feature** — Adds new CLI subcommands (`idea list`, `idea state`) and modifies the user-facing `i2code go` workflow with lifecycle state transition prompts.

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

This plan adds lifecycle management to `i2code` ideas. Ideas already live in state directories (`docs/ideas/{draft,ready,wip,completed,abandoned}/`), but there's no CLI support for listing, querying, or transitioning between states. The plan builds up incrementally:

1. A reusable **idea resolver** module that locates ideas by name across state directories
2. `idea list` and `idea state` CLI commands for lifecycle visibility and control
3. Integration into the `go` orchestrator for natural lifecycle advancement during the workflow

All tasks should be implemented using TDD (outside-in: write a failing test first, then implement). Before implementing, consult the design pattern catalog (`design-pattern-catalog/index.md`) for applicable patterns.

**Test command for this project:** `pytest` (run via `uv run pytest` or equivalent — explore existing CI and test configuration to confirm). Use markers `unit` and `integration` as appropriate.

---

## Steel Thread 1: Idea Resolver and `idea list`

Proves the new resolver module works, CLI registration works, columnar output is correct, and CI validates the new tests.

- [ ] **Task 1.1: `idea list` displays all ideas sorted alphabetically with state and directory**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea list`
  - Observable: Alphabetically sorted columnar table with columns: name, state, relative directory path. Column alignment matches `git worktree list` style. Exit code 0. Empty output (no error) when no ideas exist.
  - Evidence: `pytest` passes — tests invoke `i2code idea list` via Click CliRunner and assert alphabetical sorting, column alignment, and correct name/state/directory values
  - Steps:
    - [ ] Explore existing CLI registration in `src/i2code/cli.py`, existing `idea_cmd/` structure, `IdeaProject` class, and test organization to understand project conventions
    - [ ] Verify `.github/workflows/ci.yml` runs `pytest` (or equivalent) and will pick up new test files; modify CI if needed
    - [ ] Create `src/i2code/idea_resolver.py` with:
      - `IdeaInfo` dataclass (or similar): name, state, directory path
      - `list_ideas(git_root: Path) -> list[IdeaInfo]` — scans `docs/ideas/{draft,ready,wip,completed,abandoned}/` with `os.listdir`, returns all ideas sorted alphabetically
      - `resolve_idea(name: str, git_root: Path) -> IdeaInfo` — finds a single idea by name; raises descriptive error on no match (FR-1.3) or multiple matches (FR-1.2)
      - `state_from_path(directory: Path) -> str` — extracts lifecycle state from a directory path by parsing the state component
      - Handle missing state directories gracefully — skip them, no error (NFR-6)
      - Module must NOT import from `idea_cmd` or `go_cmd` (FR-1.5)
    - [ ] Create list command in `src/i2code/idea_cmd/` (follow existing subcommand patterns) that calls `list_ideas()` and formats columnar output with aligned columns (NFR-1)
    - [ ] Register `list` subcommand under the `idea` group in `src/i2code/cli.py`
    - [ ] Write tests:
      - Resolver `list_ideas`: multiple ideas across multiple states returns sorted list; empty when no ideas; missing state directories handled gracefully
      - Resolver `resolve_idea`: single match returns correct IdeaInfo; no match raises error with idea name; multiple matches raises error listing conflicting states
      - CLI `idea list`: output has aligned columns; multiple ideas sorted alphabetically; empty output for no ideas (exit 0)

- [ ] **Task 1.2: `idea list --state <state>` filters to a single lifecycle state**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea list --state wip`
  - Observable: Only ideas in the specified state are shown. Same columnar format. Exit code 0. Empty output (no error) when no ideas match the filter.
  - Evidence: `pytest` passes — tests invoke `i2code idea list --state <state>` via CliRunner and assert only matching ideas appear
  - Steps:
    - [ ] Add `--state` option to list command using Click `Choice` type with the five lifecycle states — this provides shell completions for free (FR-2.3)
    - [ ] Filter `list_ideas()` result by the specified state
    - [ ] Write tests: filter to state with matches shows only those ideas; filter to state with no matches shows empty output (exit 0); invalid state value rejected by Click Choice

---

## Steel Thread 2: Query Idea State

Adds the `idea state` query command that shows which lifecycle state an idea is in.

- [ ] **Task 2.1: `idea state <name-or-path>` displays current lifecycle state**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state my-feature`
  - Observable: Prints the single-word lifecycle state (e.g., `draft`). Exit code 0. Accepts both an idea name (resolved via resolver) and a directory path. Error with exit 1 if name not found.
  - Evidence: `pytest` passes — tests invoke `idea state` via CliRunner with both a name and a directory path, asserting the correct state word is printed
  - Steps:
    - [ ] Create state command in `src/i2code/idea_cmd/` with a `<name-or-path>` argument
    - [ ] Implement argument resolution: if argument is an existing directory, use it directly and extract state via `state_from_path()`; otherwise resolve via `resolve_idea()` (FR-3.2)
    - [ ] Register `state` subcommand under the `idea` group in `src/i2code/cli.py`
    - [ ] Add shell completion for `<name-or-path>` that offers both filesystem paths and idea names (FR-3.3)
    - [ ] Write tests: query by name returns correct state; query by directory path returns correct state; unknown name returns error with exit 1

---

## Steel Thread 3: Manual State Transition (Scenario 3)

Adds the transition mode to `idea state` — moving an idea between lifecycle states via `git mv` + commit.

- [ ] **Task 3.1: `idea state <name> <new-state>` moves idea directory via `git mv` and commits**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state my-feature completed`
  - Observable: Idea directory moves from `docs/ideas/wip/my-feature/` to `docs/ideas/completed/my-feature/`. Git commit created with message `Move idea my-feature from wip to completed`. Exit code 0. No-op with informational message when idea is already in the target state (FR-3.14). Exit 1 with git error message if `git mv` fails (FR-3.16).
  - Evidence: `pytest` passes — tests set up a temporary git repository with an idea directory, invoke `idea state <name> <new-state>` via CliRunner, then assert the directory moved, the old directory is gone, and a git commit exists with the expected message
  - Steps:
    - [ ] Add optional `<new-state>` argument to the state command using Click `Choice` type with the five lifecycle states — provides shell completions (FR-3.5)
    - [ ] When `<new-state>` is provided, implement transition logic:
      - No-op with message when already in target state (FR-3.14)
      - Create target state directory if it doesn't exist (`docs/ideas/<new-state>/`)
      - Execute `git mv <old-path> <new-path>` (FR-3.4)
      - Execute `git commit -m "Move idea <name> from <old-state> to <new-state>"` (FR-3.4)
      - Report git errors and exit 1 if `git mv` fails (FR-3.16)
    - [ ] Extract transition execution into a reusable function (e.g., `execute_transition(name, old_path, new_state, git_root)`) since the `go` orchestrator will reuse it in Steel Thread 6
    - [ ] Write tests (using `tmp_path` with `git init` for temporary git repos):
      - Successful transition: directory moves, commit created with correct message
      - No-op: idea already in target state prints message, exit 0, no new commit
      - Git failure: target directory already exists, reports error, exit 1

---

## Steel Thread 4: Transition Rule Enforcement (Scenarios 4 & 5)

Adds transition validation rules that enforce forward-only progression and artifact requirements, with `--force` to override.

- [ ] **Task 4.1: Transition rules enforce forward progression and artifact requirements; `--force` overrides all rules**
  - TaskType: OUTCOME
  - Entrypoint: `i2code idea state my-feature ready`
  - Observable: Blocked transitions print the violated rule and suggest `--force`. Exit 1. Specifically: `draft → ready` and `ready → wip` require a plan file to exist; backward moves (e.g., `wip → draft`) and state skips (e.g., `draft → wip`) are blocked. `any → abandoned` is always allowed. `wip → completed` is allowed unconditionally. With `--force`, all transitions proceed regardless of rules. Error messages clearly state what rule was violated (NFR-3).
  - Evidence: `pytest` passes — tests invoke `idea state` for each rule scenario (blocked and allowed) and assert correct exit codes and error/success messages
  - Steps:
    - [ ] Define the transition rule engine (can be a function or small class) that validates:
      - Linear forward progression: `draft → ready → wip → completed` (FR-3.6)
      - `draft → ready` requires plan file in idea directory (FR-3.7) — reuse existing plan file detection logic from `IdeaProject` or orchestrator
      - `ready → wip` requires plan file (FR-3.8)
      - `wip → completed` allowed unconditionally (FR-3.9)
      - `any → abandoned` always allowed (FR-3.10)
      - Backward moves require `--force` (FR-3.11)
      - Skipping states requires `--force` (FR-3.12)
    - [ ] Add `--force` flag to the state command that bypasses all rule validation (FR-3.13)
    - [ ] Wire validation into the transition flow (before `git mv`): if validation fails, print violation and suggest `--force`, exit 1 (FR-3.15)
    - [ ] Write tests:
      - `draft → ready` without plan file: blocked with message mentioning plan file requirement and `--force`
      - `draft → ready` with plan file: succeeds
      - `ready → wip` without plan file: blocked
      - `ready → wip` with plan file: succeeds
      - `wip → completed`: succeeds (no artifact check)
      - `any → abandoned`: succeeds from each state (draft, ready, wip, completed)
      - Backward move (`wip → draft`) without `--force`: blocked with message
      - Backward move with `--force`: succeeds
      - Skip states (`draft → wip`) without `--force`: blocked
      - Skip states with `--force`: succeeds

---

## Steel Thread 5: `go` Name Resolution (Scenario 6)

Allows `i2code go` to accept an idea name instead of a directory path.

- [ ] **Task 5.1: `go` accepts idea name and resolves to directory path via resolver**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go my-feature`
  - Observable: When `my-feature` is not an existing directory, the resolver finds it in the correct state directory (e.g., `docs/ideas/ready/my-feature/`) and the orchestrator proceeds with the resolved path. Error if name not found or ambiguous.
  - Evidence: `pytest` passes — tests invoke `go` with an idea name (not a directory path), verify the orchestrator receives the correct resolved directory path and proceeds normally
  - Steps:
    - [ ] Explore `src/i2code/go_cmd/` to understand how the directory argument is currently parsed and passed to the orchestrator
    - [ ] Modify the `go` command's argument handling: if the argument is not an existing directory, attempt `resolve_idea()` from the resolver (FR-4.1, FR-4.2)
    - [ ] Add shell completions for the argument that offer both filesystem paths and idea names (FR-4.3)
    - [ ] Write tests:
      - `go` with idea name resolves to correct directory and orchestrator proceeds
      - `go` with directory path still works unchanged (backward compatible)
      - `go` with unknown name shows resolver error

---

## Steel Thread 6: `go` HAS_PLAN Menu Integration (Scenario 2)

The HAS_PLAN menu becomes dynamic based on the idea's lifecycle state, offering forward state transitions.

- [ ] **Task 6.1: HAS_PLAN menu shows lifecycle move option based on idea state**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go my-feature` (idea in `draft/` with plan file)
  - Observable: Menu shows "Move idea to ready" as option 2 and default when idea is in `draft/` (FR-5.1). Menu shows "Move idea to wip" as option 2 and default when idea is in `ready/` (FR-5.2). Menu shows no move option when idea is in `wip/`, `completed/`, or `abandoned/`, with "Implement" as default (FR-5.3). The "Commit changes" option continues to appear dynamically when uncommitted changes exist (FR-5.5).
  - Evidence: `pytest` passes — tests verify the menu structure returned by the orchestrator for each lifecycle state (draft, ready, wip)
  - Steps:
    - [ ] Explore the HAS_PLAN menu construction in `src/i2code/go_cmd/orchestrator.py` to understand how menu options are built and how the default is set
    - [ ] Determine idea lifecycle state from `IdeaProject` directory path using `state_from_path()` from the resolver module
    - [ ] Modify HAS_PLAN menu construction:
      - When state is `draft`: insert "Move idea to ready" as option 2, make it default (FR-5.1)
      - When state is `ready`: insert "Move idea to wip" as option 2, make it default (FR-5.2)
      - When state is `wip`/`completed`/`abandoned`: no move option, "Implement" is default (FR-5.3)
    - [ ] Write tests: menu for draft idea with plan has move-to-ready as default; menu for ready idea has move-to-wip as default; menu for wip idea has no move option and implement as default

- [ ] **Task 6.2: Selecting move option transitions idea and re-enters menu with updated state**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go my-feature` → select "Move idea to ready"
  - Observable: Idea moves from `draft/` to `ready/` via `git mv` + commit (same mechanism as `idea state`). IdeaProject instance is replaced with one pointing to the new directory (FR-6.1). All subsequent operations use the updated path (FR-6.2). Menu re-appears with updated options reflecting the new state (e.g., now shows "Move idea to wip" as default).
  - Evidence: `pytest` passes — tests simulate selecting the move menu option, verify the transition occurred (directory moved, commit created), verify the IdeaProject was rebuilt with the new path, and verify the menu re-enters with updated options
  - Steps:
    - [ ] Implement the move menu handler: reuse the transition execution function from Steel Thread 3
    - [ ] After transition, reconstruct `IdeaProject` with the new directory path (FR-6.1)
    - [ ] Re-enter the HAS_PLAN menu loop so the user sees the updated menu (FR-6.2)
    - [ ] Write tests:
      - Select move from draft: idea transitions to ready, IdeaProject path updated, menu re-enters showing "Move to wip" as default
      - Select move from ready: idea transitions to wip, IdeaProject path updated, menu re-enters with no move option and "Implement" as default
      - After move, orchestrator uses new path for subsequent operations (e.g., plan file path resolves from new directory)
