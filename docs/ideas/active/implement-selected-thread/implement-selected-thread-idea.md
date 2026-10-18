# Implement Selected Thread

## Problem

`i2code implement --trunk` runs every incomplete task in the plan, thread after thread, until the plan is complete. The user cannot stop after one thread to review its commits before the next thread starts.

## Goal

Add a `--thread N` option to `i2code implement` trunk mode that runs the incomplete tasks of thread N only, then stops.

```
i2code implement --trunk --thread 3 my-idea
```

The user runs one thread, reviews the commits on the current branch, then runs the next thread with another `--thread` invocation.

## Behaviour

- **Trunk mode only:** `--thread` without `--trunk` is a usage error. Worktree and isolate modes do not support it.
- **Order is enforced:** if any thread before N has incomplete tasks, i2code exits with an error naming those threads.
- **Stopping:** after thread N's last task completes, i2code reports that thread N is complete and names the next thread when one remains. When thread N was the last thread with incomplete tasks, it reports that all tasks are complete, as today.
- **Thread already complete:** i2code reports it and exits with status 0.
- **Thread does not exist:** usage error naming the valid range.
- **Commit recovery:** `commit_if_needed` still runs before the first task.
- **Validation before work:** the mode, the thread number and the earlier threads are checked before any task runs.
- **Other options:** `validate_trunk_options` already rejects `--trunk` combined with `--isolate`, `--address-review-comments` and the other worktree-only options, so `--thread` needs no extra checks for them.

## Out of scope

- `--thread` in worktree and isolate modes, including PR state between threads and review-comment polling.
- Running threads in parallel, each with its own branch and PR.
- Running a later thread before earlier ones.
- A "next thread" option or flag, and any change to the `i2code go` menu.

## Locations

- `src/i2code/implement/cli.py:55` — `implement_cmd`, where `--thread` is added
- `src/i2code/implement/implement_opts.py:9` — `ImplementOpts`; the `--thread` requires `--trunk` check goes alongside `validate_trunk_options` (`src/i2code/implement/implement_opts.py:66`)
- `src/i2code/implement/implement_command.py:23` — `execute`, where validation runs before mode selection
- `src/i2code/implement/implement_command.py:47` — `_trunk_mode`
- `src/i2code/implement/trunk_mode.py:24` — task loop that calls `get_next_task()`
- `src/i2code/implement/idea_project.py:132` — `get_next_task`
- `src/i2code/plan_domain/plan.py:53` — `get_thread`
- `src/i2code/plan_domain/plan.py:58` — `get_next_task`, which walks all threads
