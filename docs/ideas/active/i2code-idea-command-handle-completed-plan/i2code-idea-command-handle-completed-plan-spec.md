# Specification: Bulk-Complete Ideas with Finished Plans

## Purpose and Background

The `i2code` idea lifecycle requires manual state transitions even when the system has enough information to determine the next state. Specifically, when all tasks in an idea's plan are marked complete, the idea's metadata state remains `wip` until the user explicitly runs `i2code idea state <name> completed` for each idea individually.

This creates a workflow gap between two existing automated bulk operations:
- `i2code implement` — marks plan tasks as complete during implementation
- `i2code idea archive --completed` — bulk-archives all ideas in `completed` state

The missing middle step — transitioning `wip` ideas with fully-completed plans to `completed` — is currently manual and per-idea.

## Target Users

Developers using `i2code` to manage multiple ideas through the brainstorm → spec → plan → implement → archive lifecycle. These users run `i2code idea archive --completed` to clean up their working set and expect a similarly convenient way to mark ideas as completed when their plans are done.

## Problem Statement

After implementation finishes, users must:
1. Remember which ideas have fully-completed plans
2. Manually transition each one: `i2code idea state <name> completed`
3. Then bulk-archive: `i2code idea archive --completed`

Step 2 is tedious when multiple ideas finish in the same session and is easy to forget, leaving stale `wip` ideas in the active set.

## Goals

1. Allow users to bulk-transition all `wip` ideas with fully-completed plans to `completed` in a single command.
2. Follow established CLI patterns (`archive --completed`) for consistency.
3. Produce a single git commit for the bulk operation.

## In Scope

- New `--completed-plans` flag on the `i2code idea state` command
- Scanning active ideas in `wip` state for fully-completed plans
- Transitioning matching ideas to `completed` state
- Single git commit for all transitions
- `--no-commit` support
- Informational output for each transitioned idea and when no matches are found

## Out of Scope

- Automatic transition during `i2code implement` (this remains a separate, explicit step)
- Combining `--completed-plans` with `--completed` on `idea archive` (users run two commands)
- Transitioning ideas from states other than `wip` (transition rules enforce `wip → completed`)
- Interactive confirmation before transitioning

## High-Level Functional Requirements

### FR-1: `--completed-plans` flag

Add a `--completed-plans` boolean flag to the `idea state` Click command.

### FR-2: Mutual exclusivity with `<name>` argument

When `--completed-plans` is provided, the `name_or_path` argument must not be provided. If both are given, raise a `click.UsageError` with the message: `"Provide an idea name or use --completed-plans, not both."`

When neither `--completed-plans` nor `name_or_path` is provided, raise a `click.UsageError` with the message: `"Provide an idea name or use --completed-plans."`

### FR-3: Scan active `wip` ideas

Use `list_ideas(git_root)` to find all active ideas. Filter to ideas where:
- `idea.state == "wip"`
- The idea directory is under `docs/ideas/active/`

### FR-4: Detect fully-completed plans

For each `wip` idea, construct the plan file path using the `IdeaProject` convention: `<idea-dir>/<name>-plan.md`. If the plan file exists:
- Parse it using the plan domain parser
- Check that the plan has at least one task (`plan.task_progress().total > 0`)
- Check that all tasks are complete (`plan.get_next_task() is None`)

Ideas without a plan file or with an empty plan (zero tasks) are skipped silently.

### FR-5: Transition matching ideas

For each matching idea, call `execute_transition(idea.name, idea_dir, "completed", git_root)` to update the metadata file and stage it. Print the returned commit message for each idea (e.g., `"Move idea my-idea from wip to completed"`).

### FR-6: Single git commit

After all transitions are staged, create a single commit with the message:
`"Mark ideas with completed plans as completed: idea-a, idea-b, idea-c"`

where the idea names are comma-separated in the order they were processed.

### FR-7: Empty result handling

If no `wip` ideas with fully-completed plans are found, print `"No wip ideas with completed plans found"` to stdout and exit 0. No commit is created.

### FR-8: `--no-commit` support

When `--no-commit` is provided, stage the metadata changes but do not create a git commit. This is consistent with `idea state --no-commit` and `idea archive --no-commit`.

## Security Requirements

This is a local CLI tool with no network endpoints or multi-user access. All operations run as the current OS user with their filesystem and git permissions. No authorization checks are required beyond standard filesystem access.

## Non-Functional Requirements

### Consistency
- The flag name `--completed-plans` follows the `--completed` naming pattern established by `idea archive`.
- Output format follows the existing `idea state` and `archive --completed` patterns.
- `--no-commit` behavior is identical to other commands.

### Correctness
- Only ideas in `wip` state are considered (enforced by filtering, not by calling `validate_transition`).
- Plans must have at least one task to qualify — an empty plan file does not count as "completed."
- The `execute_transition` function is reused to ensure metadata updates follow the same code path as single-idea transitions.

### Performance
- No performance requirements beyond existing CLI responsiveness. The scan iterates over active ideas and parses plan files, which is bounded by the number of active ideas (typically < 20).

## Success Metrics

1. Users can transition all finished ideas in a single command instead of one command per idea.
2. The typical post-implementation workflow becomes two commands:
   ```
   i2code idea state --completed-plans
   i2code idea archive --completed
   ```

## Epics and User Stories

### Epic: Bulk-complete ideas with finished plans

**US-1:** As a developer, I want to run `i2code idea state --completed-plans` so that all my `wip` ideas with fully-completed plans are transitioned to `completed` without me having to check each one manually.

**US-2:** As a developer, I want to see which ideas were transitioned so I can verify the command did what I expected.

**US-3:** As a developer, I want to be informed when no ideas match so I know the command ran successfully but found nothing to do.

**US-4:** As a developer, I want to use `--no-commit` with `--completed-plans` so I can review the staged changes before committing.

## User-Facing Scenarios

### Scenario 1: Primary — Multiple wip ideas with completed plans (end-to-end)

**Given** three active ideas in `wip` state:
- `idea-a` has a plan with all tasks marked `[x]`
- `idea-b` has a plan with all tasks marked `[x]`
- `idea-c` has a plan with one task still `[ ]`

**When** the user runs `i2code idea state --completed-plans`

**Then:**
- `idea-a` and `idea-b` are transitioned to `completed`
- `idea-c` remains in `wip`
- Output shows:
  ```
  Move idea idea-a from wip to completed
  Move idea idea-b from wip to completed
  ```
- A single git commit is created: `"Mark ideas with completed plans as completed: idea-a, idea-b"`

### Scenario 2: No matching ideas

**Given** no active `wip` ideas have fully-completed plans

**When** the user runs `i2code idea state --completed-plans`

**Then:**
- Output: `"No wip ideas with completed plans found"`
- Exit code: 0
- No git commit is created

### Scenario 3: With `--no-commit`

**Given** one active `wip` idea (`idea-x`) with a fully-completed plan

**When** the user runs `i2code idea state --completed-plans --no-commit`

**Then:**
- `idea-x` metadata is updated and staged
- Output: `"Move idea idea-x from wip to completed"`
- No git commit is created

### Scenario 4: Mutual exclusivity error

**When** the user runs `i2code idea state my-idea --completed-plans`

**Then:**
- Error: `"Provide an idea name or use --completed-plans, not both."`
- Exit code: non-zero

### Scenario 5: Wip idea without a plan file

**Given** an active `wip` idea (`idea-no-plan`) that has no plan file

**When** the user runs `i2code idea state --completed-plans`

**Then:**
- `idea-no-plan` is skipped silently
- If no other ideas match, output: `"No wip ideas with completed plans found"`

### Scenario 6: Wip idea with an empty plan (zero tasks)

**Given** an active `wip` idea (`idea-empty`) whose plan file exists but contains no tasks

**When** the user runs `i2code idea state --completed-plans`

**Then:**
- `idea-empty` is skipped silently (a plan with zero tasks is not considered "completed")
