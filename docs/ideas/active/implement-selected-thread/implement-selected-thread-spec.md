# Implement Selected Thread — Platform Capability Specification

## Purpose and context

`i2code implement --trunk <idea-directory>` runs plan tasks on the current branch, with no worktree, PR or CI. `TrunkMode.execute` (`src/i2code/implement/trunk_mode.py:24`) loops on `IdeaProject.get_next_task()`, which calls `Plan.get_next_task()` (`src/i2code/plan_domain/plan.py:58`). That method walks every thread in order and returns the first incomplete task, so a trunk run continues until the whole plan is complete.

A developer who wants to review each steel thread before the next one starts has no way to stop at a thread boundary. This capability adds a `--thread N` option to `i2code implement`. In trunk mode, it runs the incomplete tasks of thread N only, then exits. The developer reviews the thread's commits, then runs the next thread with another invocation.

## Consumers

- **Developers driving the idea-to-code workflow** who run `i2code implement --trunk` from a shell and want to review the work thread by thread.
- **Scripts and tests** that invoke `i2code implement`, including tests that use `--mock-claude`. They rely on the exit codes and messages defined below.

The `i2code go` orchestrator is not a consumer. Its menu and its `implement_runner` (`src/i2code/go_cmd/orchestrator.py:143`) do not change.

## Capabilities and behaviors

### C1. Select a thread

`i2code implement --trunk --thread N <idea-directory>` runs the incomplete tasks of thread N, where N is the 1-based thread number as it appears in the plan's `## Steel Thread N: <title>` headings.

On each loop iteration, trunk mode re-reads the plan file and picks the first incomplete task in thread N. It runs that task exactly as it runs a task today: the same Claude command, the same three attempts, the same checks that HEAD moved, that `<SUCCESS>` is in the output in non-interactive mode, and that the task is marked complete in the plan file.

Tasks in other threads are never run during a `--thread` run.

### C2. Require trunk mode

`--thread` is supported only with `--trunk`. When `--thread` is given without `--trunk`, i2code raises `click.UsageError("--thread requires --trunk")`, which Click reports as `Error: --thread requires --trunk` and exit status 2. This applies to worktree mode and to isolate mode, including when isolate mode is implied by `--isolation-type` or `--shell`.

The existing check `ImplementOpts.validate_trunk_options` (`src/i2code/implement/implement_opts.py:66`) already rejects `--trunk` combined with `--cleanup`, `--setup-only`, `--isolate`, `--isolated`, `--skip-ci-wait`, `--address-review-comments`, `--ci-fix-retries` and `--ci-timeout`. Those checks also cover `--thread`, because `--thread` requires `--trunk`.

### C3. Validate the thread number

When N is less than 1 or greater than the number of threads in the plan, i2code raises `click.UsageError("--thread must be between 1 and <T>")`, where `<T>` is the number of threads. Click reports it with exit status 2.

The value must be an integer. Click's `type=int` rejects a non-integer value with its standard message and exit status 2.

### C4. Enforce thread order

When any thread numbered below N has an incomplete task, i2code prints to stderr:

```
Error: Cannot run thread 3: earlier threads have incomplete tasks: 1, 2
```

and exits with status 1. The list names every earlier thread that has at least one incomplete task, in ascending order, separated by `, `.

### C5. Report an already complete thread

When thread N has no incomplete tasks, i2code prints:

```
[HH:MM:SS] Thread 3 (<title>) is already complete.
```

followed by the next-thread line from C6, and exits with status 0. No Claude command runs.

The order check in C4 runs before this check, so a complete thread N with an incomplete earlier thread is an error.

### C6. Stop after the thread

When thread N has no incomplete task left, trunk mode prints one of these and exits with status 0:

- When a later thread has an incomplete task, it prints `[HH:MM:SS] Thread 3 (<title>) is complete.` followed by `[HH:MM:SS] Next: i2code implement --trunk --thread 4 <idea-directory>`. The next thread is the lowest-numbered thread with an incomplete task. `<idea-directory>` is the resolved idea directory that i2code was given.
- When no thread has an incomplete task, it prints `[HH:MM:SS] All tasks completed!`, the message trunk mode prints today.

`<title>` is `Thread.title` (`src/i2code/plan_domain/thread.py:15`). The `[HH:MM:SS]` prefix comes from `print_message` (`src/i2code/implement/console.py:6`).

### C7. Keep existing trunk behavior

A `--thread` run keeps everything else trunk mode does:

- `TaskCommitRecovery.commit_if_needed` runs before the first task.
- Each attempt prints `Executing task (attempt <a>/3): <task description>`.
- A task that fails after three attempts prints `Error: Task failed after 3 attempts.` and exits with status 1.
- `--non-interactive`, `--extra-prompt`, `--mock-claude` and `--debug-claude` behave as they do today.

### C8. Validate before running any task

The checks in C2, C3, C4 and C5 all complete before `commit_if_needed` runs and before any Claude command runs. C2 runs during option validation, before the idea-file commit check. C3, C4 and C5 read the plan file.

### C9. Dry run

`--dry-run` with `--thread N` still applies C2, then prints `[HH:MM:SS] Thread: N` after the existing `Mode`, `Idea` and `Directory` lines, and exits with status 0. It does not apply C3, C4 or C5.

### C10. Runs without `--thread`

When `--thread` is not given, every mode behaves exactly as it does today.

## APIs, contracts and integration points

### Command line

```
i2code implement --trunk --thread <N> [other trunk options] <idea-directory>
```

| Option | Type | Default | Help text |
|--------|------|---------|-----------|
| `--thread` | integer, metavar `N` | none | `Implement only the incomplete tasks of thread N, then stop (requires --trunk)` |

### Exit status

| Situation | Status |
|-----------|--------|
| Thread N completed, or already complete | 0 |
| `--dry-run` | 0 |
| `--thread` without `--trunk`, out-of-range or non-integer N | 2 (Click usage error) |
| Earlier thread has incomplete tasks | 1 |
| Task failed after three attempts, or non-interactive run without `<SUCCESS>` | 1 (unchanged) |

### Code integration points

- `ImplementOpts` (`src/i2code/implement/implement_opts.py:9`) gains `thread: int | None = None`. `thread` is added to `_INNER_IGNORED`, because isolate mode never forwards it: C2 rejects `--thread` in isolate mode.
- `implement_cmd` (`src/i2code/implement/cli.py:55`) gains the `--thread` option.
- `ImplementCommand.execute` (`src/i2code/implement/implement_command.py:23`) applies C2 during validation and C9 in `_print_dry_run`.
- `TrunkMode.execute` (`src/i2code/implement/trunk_mode.py:24`) applies C3 to C6 when `opts.thread` is set. `TrunkMode` already receives `opts` from `ModeFactory.make_trunk_mode` (`src/i2code/implement/mode_factory.py:24`).
- `IdeaProject` (`src/i2code/implement/idea_project.py:132`) and `Plan` (`src/i2code/plan_domain/plan.py`) provide the plan queries the checks need: the number of threads, the first incomplete task in a given thread, the earlier threads with incomplete tasks, and a thread's title. `Plan.get_thread` (`src/i2code/plan_domain/plan.py:53`) already raises `ValueError` for an out-of-range number.

The plan file format and the `i2code plan` CLI do not change.

## Non-functional requirements

- **No new dependencies.** The option uses Click and the existing plan domain.
- **Plan reads stay cheap.** Each check opens the plan file with the existing `with_plan_file` helper. The validation in C3 to C5 adds a constant number of plan reads per run.
- **Type checks and code health.** `uvx pyright --level error src/` reports no errors, and modified files keep a CodeScene Code Health score of 10.0, as `CLAUDE.md` requires.
- **Tests.** Behavior is covered by `unit`-marked pytest tests that use `--mock-claude` or fakes; no test calls the Claude API.

## Scenarios and workflows

### Primary end-to-end scenario: review thread by thread

1. A plan for idea `my-idea` has three threads, all incomplete. The idea files are committed.
2. The developer runs `i2code implement --trunk --thread 1 docs/ideas/active/my-idea`.
3. i2code validates the options and the plan, runs `commit_if_needed`, then runs each task of thread 1 in order. Claude commits each task and marks it complete in the plan file.
4. When thread 1 has no incomplete task, i2code prints `Thread 1 (<title>) is complete.` and `Next: i2code implement --trunk --thread 2 docs/ideas/active/my-idea`, then exits with status 0.
5. The developer reviews thread 1's commits on the current branch.
6. The developer runs the printed command for thread 2, then for thread 3.
7. After thread 3's last task, i2code prints `All tasks completed!` and exits with status 0.

### Scenario: thread run out of order

Thread 1 is complete and thread 2 has incomplete tasks. The developer runs `i2code implement --trunk --thread 3 my-idea`. i2code prints `Error: Cannot run thread 3: earlier threads have incomplete tasks: 2` and exits with status 1. No task runs and no commit is made.

### Scenario: thread already complete

Threads 1 and 2 are complete and thread 3 is not. The developer runs `--thread 2`. i2code prints `Thread 2 (<title>) is already complete.` and `Next: i2code implement --trunk --thread 3 <idea-directory>`, then exits with status 0.

### Scenario: thread number out of range

The plan has three threads. `--thread 4` and `--thread 0` each exit with `Error: --thread must be between 1 and 3` and status 2.

### Scenario: `--thread` without `--trunk`

`i2code implement --thread 2 my-idea` and `i2code implement --isolate --thread 2 my-idea` each exit with `Error: --thread requires --trunk` and status 2. No branch, worktree, clone or PR is created.

### Scenario: task fails inside the thread

A task in thread 2 fails all three attempts. i2code prints `Error: Task failed after 3 attempts.` and exits with status 1, as today. Rerunning `--thread 2` resumes at the first incomplete task of thread 2.

### Scenario: interrupted run with an uncommitted completed task

A previous `--thread 2` run was interrupted after Claude marked a task complete but before it committed. The next `--thread 2` run's `commit_if_needed` commits that work, as it does today, then continues with thread 2's next incomplete task.

## Constraints and assumptions

- **Trunk mode only.** Worktree and isolate modes reject `--thread` (Q7 in the discussion file).
- **Threads run in order.** A thread runs only when every earlier thread is complete (Q3).
- **One thread per run.** The option takes a single thread number. There is no range, list, or "next thread" form (Q2).
- **Re-reading the plan.** Because the plan is re-read before each task, a task added to thread N during the run is picked up by the same run. A task added to an earlier thread during the run does not stop the run; the C4 check applies only at the start.
- **Exit status 1 for the order check.** The order check depends on the plan's state, not on how the command was typed, so it uses the same `Error: ...` and status 1 style as other plan-state errors such as `Error: Plan file not found`.
- **Dry run does not read thread state.** `--dry-run` reports the selected thread without checking it, matching today's dry run, which prints the mode without checking the plan's tasks.
- **`i2code go` is unchanged** (Q6).

## Acceptance criteria

1. `i2code implement --trunk --thread N <dir>` runs every incomplete task of thread N, in order, and runs no task from any other thread.
2. After thread N's last task, the run prints `Thread N (<title>) is complete.` and the `Next:` line naming the lowest-numbered incomplete thread, then exits with status 0. When the plan is complete, it prints `All tasks completed!` instead.
3. `--thread` without `--trunk`, including with `--isolate`, `--isolation-type` or `--shell`, exits with `Error: --thread requires --trunk` and status 2 before any branch, worktree, clone or PR is created.
4. An out-of-range N exits with `Error: --thread must be between 1 and <T>` and status 2.
5. An incomplete earlier thread exits with `Error: Cannot run thread N: earlier threads have incomplete tasks: <list>` and status 1, and no Claude command runs.
6. An already complete thread N prints `Thread N (<title>) is already complete.` and the `Next:` line, exits with status 0, and no Claude command runs.
7. `--dry-run --trunk --thread N` prints `Thread: N` after the existing dry-run lines.
8. Runs without `--thread` behave as before in every mode; the existing implement tests pass unchanged.
9. `uvx pyright --level error src/` reports no errors, and modified files have a CodeScene Code Health score of 10.0.
