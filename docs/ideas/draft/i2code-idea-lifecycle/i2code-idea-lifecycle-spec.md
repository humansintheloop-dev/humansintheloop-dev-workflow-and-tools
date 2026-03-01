# i2code idea lifecycle — Specification

## Purpose and Background

The `i2code` CLI guides developers through an idea-to-implementation workflow: brainstorm, specify, design, plan, implement. Ideas live in `docs/ideas/{state}/{name}/` directories where `state` is one of `draft`, `ready`, `wip`, `completed`, or `abandoned`. Today, the directory state is managed entirely by hand — there are no CLI commands to list ideas, query their state, or transition them. The `i2code go` orchestrator detects *workflow* state (which artifacts exist) but is unaware of *lifecycle* state (which directory the idea lives in). As a result, ideas stagnate in `draft/` or `ready/` long after work has begun.

## Target Users

Solo developers and small teams using the `i2code` CLI to manage idea-to-code workflows.

## Problem Statement

1. No way to list ideas or filter by lifecycle state from the CLI.
2. No way to transition an idea between states from the CLI — requires manual `git mv`.
3. The `go` orchestrator does not surface lifecycle transitions, so ideas never advance through `draft → ready → wip`.
4. `go` only accepts directory paths, which become invalid after a state transition moves the directory.

## Goals

- Provide `idea list` and `idea state` subcommands for lifecycle visibility and control.
- Integrate forward lifecycle transitions into the `go` orchestrator's HAS_PLAN menu.
- Allow `go` and `idea` commands to accept an idea name (not just a directory path).
- Provide shell completions for idea names and state values.

## In Scope

- `i2code idea list` command with `--state` filter
- `i2code idea state` command (query and transition)
- Transition rule enforcement with `--force` override
- Idea name resolver (reusable module)
- `i2code go` name resolution and HAS_PLAN menu integration
- Shell completions for idea names and state values
- Git operations (`git mv` + commit) for state transitions

## Out of Scope

- End-of-lifecycle transitions in `go` (`wip → completed`, `wip → abandoned`) — manual only
- Name resolution for other commands (`spec`, `design`, `brainstorm`) — future enhancement
- Idea templates or scaffolding
- Remote/multi-repo idea tracking
- Notification or webhook integration

## Functional Requirements

### FR-1: Idea Name Resolver

A reusable module that locates an idea directory by name across all state directories.

- **FR-1.1**: Given an idea name, scan `{git-root}/docs/ideas/{draft,ready,wip,completed,abandoned}/{name}/` and return the matching directory path and state.
- **FR-1.2**: If the name matches directories in multiple states, return an error (an idea must exist in exactly one state).
- **FR-1.3**: If no match is found, return an error.
- **FR-1.4**: The ideas root is `docs/ideas/` relative to the git repository root.
- **FR-1.5**: The module must not depend on `idea_cmd` or `go_cmd` so other commands can adopt it later.

### FR-2: `idea list` Command

- **FR-2.1**: `i2code idea list` prints a flat, alphabetically sorted table with columns: name, state, relative directory path. Column alignment matches `git worktree list` style.
- **FR-2.2**: `i2code idea list --state <state>` filters to a single state. Same columnar format.
- **FR-2.3**: Shell completions for `--state` values (the five lifecycle states).
- **FR-2.4**: Exit code 0 on success. Empty output (no error) when no ideas match.

### FR-3: `idea state` Command

#### Query mode

- **FR-3.1**: `i2code idea state <name-or-path>` prints the current lifecycle state of the idea (e.g., `draft`).
- **FR-3.2**: The `<name-or-path>` argument accepts either an idea name (resolved via FR-1) or a directory path. If the argument is an existing directory, use it directly; otherwise attempt name resolution.
- **FR-3.3**: Shell completion for `<name-or-path>` offers both filesystem path completion and idea name completion.

#### Transition mode

- **FR-3.4**: `i2code idea state <name-or-path> <new-state>` moves the idea directory via `git mv` and creates a commit with message `Move idea <name> from <old-state> to <new-state>`.
- **FR-3.5**: Shell completion for `<new-state>` (the five lifecycle states).

#### Transition rules

- **FR-3.6**: Forward transitions follow the linear progression: `draft → ready → wip → completed`.
- **FR-3.7**: `draft → ready` requires a plan file to exist in the idea directory.
- **FR-3.8**: `ready → wip` requires a plan file to exist in the idea directory.
- **FR-3.9**: `wip → completed` is allowed with no additional artifact check.
- **FR-3.10**: `any → abandoned` is always allowed.
- **FR-3.11**: Backward moves (e.g., `wip → draft`) require the `--force` flag.
- **FR-3.12**: Skipping states (e.g., `draft → wip`) requires the `--force` flag.
- **FR-3.13**: `--force` bypasses both transition ordering and artifact validation.

#### Error handling

- **FR-3.14**: If the idea is already in the target state, print a message and exit 0 (no-op).
- **FR-3.15**: If a transition rule is violated, print the rule and suggest `--force`. Exit 1.
- **FR-3.16**: If `git mv` fails (e.g., target directory already exists), report the git error. Exit 1.

### FR-4: `go` Command — Name Resolution

- **FR-4.1**: `i2code go` accepts either a directory path or an idea name as its argument.
- **FR-4.2**: If the argument is not an existing directory, attempt to resolve it as an idea name via the resolver.
- **FR-4.3**: Shell completions offer both filesystem path completion and idea name completion.

### FR-5: `go` Command — HAS_PLAN Menu Integration

The HAS_PLAN menu becomes dynamic based on the idea's lifecycle state.

- **FR-5.1**: When the idea is in `draft/`, the menu is:
  ```
  1. Revise the plan
  2. Move idea to ready  [default]
  3. Implement the entire plan
  4. Configure implement options
  5. Exit
  ```

- **FR-5.2**: When the idea is in `ready/`, the menu is:
  ```
  1. Revise the plan
  2. Move idea to wip  [default]
  3. Implement the entire plan
  4. Configure implement options
  5. Exit
  ```

- **FR-5.3**: When the idea is in `wip/` (or `completed/` or `abandoned/`), the menu is unchanged from today (no move option, Implement is default):
  ```
  1. Revise the plan
  2. Implement the entire plan  [default]
  3. Configure implement options
  4. Exit
  ```

- **FR-5.4**: When the user selects a move option, execute the transition (same `git mv` + commit as `idea state`) and reconstruct the internal `IdeaProject` with the new path. Then re-enter the menu loop with the updated state.
- **FR-5.5**: The "Commit changes" option continues to appear dynamically when uncommitted changes exist (inserted before "Implement" as it does today).

### FR-6: IdeaProject Update After Move

- **FR-6.1**: After a state transition in `go`, the orchestrator must replace its `IdeaProject` instance with one pointing to the new directory.
- **FR-6.2**: All subsequent operations in the same `go` session use the updated path.

## Non-Functional Requirements

### UX

- **NFR-1**: `idea list` output is columnar and aligned, readable without piping to other tools.
- **NFR-2**: Shell completions work in bash and zsh (Click's built-in completion support).
- **NFR-3**: Error messages for invalid transitions clearly state what rule was violated and how to override.

### Performance

- **NFR-4**: `idea list` and name resolution scan at most 5 state directories with a single `os.listdir` each. No recursive file walks.

### Reliability

- **NFR-5**: State transitions are atomic at the git level — `git mv` + `git commit` in sequence. If `git mv` fails, no commit is created.
- **NFR-6**: The resolver handles missing state directories gracefully (e.g., if `docs/ideas/abandoned/` does not exist, skip it).

## Success Metrics

- All five lifecycle states are reachable via `idea state` without manual `git mv`.
- `go` users naturally advance ideas through `draft → ready → wip` via menu selections.
- `idea list` provides a quick overview of all ideas and their states.

## Epics and User Stories

### Epic 1: Idea Name Resolver

- **US-1.1**: As a developer, I can pass an idea name to `i2code go` instead of a directory path, so I don't need to remember which state directory the idea is in.
- **US-1.2**: As a developer, I see a clear error if an idea name doesn't match any directory or matches multiple directories.

### Epic 2: Idea List

- **US-2.1**: As a developer, I can run `i2code idea list` to see all ideas sorted alphabetically with their state and directory.
- **US-2.2**: As a developer, I can run `i2code idea list --state wip` to see only ideas in progress.

### Epic 3: Idea State

- **US-3.1**: As a developer, I can run `i2code idea state my-feature` to see which lifecycle state an idea is in.
- **US-3.2**: As a developer, I can run `i2code idea state my-feature ready` to move an idea to `ready/` with a git commit.
- **US-3.3**: As a developer, I see an error if I try to move `draft → ready` without a plan file, with a suggestion to use `--force`.
- **US-3.4**: As a developer, I can run `i2code idea state my-feature draft --force` to move an idea backward.

### Epic 4: Go Integration

- **US-4.1**: As a developer using `i2code go`, I see "Move idea to ready" as the default menu option when my idea is in `draft/` with a plan.
- **US-4.2**: As a developer using `i2code go`, I see "Move idea to wip" as the default menu option when my idea is in `ready/`.
- **US-4.3**: As a developer using `i2code go`, after selecting a move option the menu re-appears with updated options reflecting the new state.

## Scenarios

### Scenario 1: List and filter ideas (primary end-to-end scenario)

Developer has several ideas in various states. They run `idea list` to get an overview, then filter to `--state draft` to see what needs attention.

### Scenario 2: Advance an idea through the full lifecycle via `go`

Developer starts `i2code go my-feature` with an idea in `draft/` that has a plan. They select "Move idea to ready" from the menu. The menu re-appears; they select "Move idea to wip". The menu re-appears; they select "Implement the entire plan".

### Scenario 3: Manual state transition with `idea state`

Developer finishes implementation and runs `i2code idea state my-feature completed` to move the idea to `completed/`.

### Scenario 4: Blocked transition with override

Developer tries `i2code idea state my-feature ready` but no plan file exists. The CLI reports the violation. Developer runs `i2code idea state my-feature ready --force` to override.

### Scenario 5: Backward transition

Developer realizes an idea in `wip/` needs rework. They run `i2code idea state my-feature draft --force` to move it back.

### Scenario 6: Name resolution in `go`

Developer runs `i2code go my-feature` (just the name). The resolver finds the idea in `docs/ideas/ready/my-feature/` and the orchestrator proceeds normally.
