# Implement Selected Thread — Discussion

## Codebase context

- `TrunkMode.execute` (`src/i2code/implement/trunk_mode.py:24`) and `WorktreeMode.execute` (`src/i2code/implement/worktree_mode.py:65`) both loop on `IdeaProject.get_next_task()`, which calls `Plan.get_next_task()` (`src/i2code/plan_domain/plan.py:58`). That walks every thread in order and returns the first incomplete task.
- Worktree mode uses one idea branch, one worktree and one Draft PR per idea. When no task is left, `_print_completion` marks the PR ready for review.
- Isolate mode forwards options to the inner `i2code implement` through `ImplementOpts._INNER_FORWARDED` (`src/i2code/implement/implement_opts.py:28`).

## Q1: What is the main reason for implementing a single thread?

Options: stop for review; run independent threads in parallel, each with its own branch and PR; implement a later thread out of order; several of these.

**Answer:** Stop for review. Run one thread on the idea's usual branch and PR, then stop so the user can review before the next thread runs.

## Q2: How should the user choose which thread to run?

Options: `--thread N` (explicit thread number); a flag that runs the thread containing the next incomplete task; both.

**Answer:** Thread number: `i2code implement --thread 3 my-idea` runs the incomplete tasks of thread 3 only.

## Q3: What should `--thread N` do when an earlier thread still has incomplete tasks?

Options: run anyway; warn and run; refuse.

**Answer:** Refuse. Exit with an error naming the incomplete earlier threads. Threads must be done in order.

## Q4: In worktree mode, what should happen to the Draft PR when thread N finishes but later threads remain?

Options: keep it draft; mark it ready after each thread; mark it ready, then convert back to draft when the next thread starts.

**Answer:** Keep it draft. The PR is marked ready only when the last task of the plan completes, as today. The user reviews the draft PR between threads.

**Derived:** when thread N is the last thread with incomplete tasks, finishing it completes the plan, so the PR is marked ready as today.

## Q5: What should `--address-review-comments` do with `--thread N` when later threads remain?

Options: reject the combination; poll until the user stops it; address existing comments once, then stop.

**Answer:** Reject the combination. `--thread N` with `--address-review-comments` is a usage error unless thread N is the last thread with incomplete tasks. Comments left on the draft PR are still handled at the start of the next run, because the worktree loop calls `process_feedback` before each task.

## Q6: Should `i2code go` offer running a single thread?

Options: yes, add an option that runs the first thread with incomplete tasks; no, CLI only.

**Answer:** No, CLI only. Only `i2code implement --thread N` is added. The go menu is unchanged and can be extended in a separate idea.

## Q7 (raised by the user at the closing question): Which modes support `--thread`?

**Answer:** Trunk mode only. `--thread` is rejected in worktree and isolate modes.

**Derived:**
- `--thread` without `--trunk` is a usage error.
- Trunk mode has no PR, CI build or review comments, so the answers to Q4 (PR stays draft) and Q5 (`--address-review-comments`) no longer apply. `validate_trunk_options` (`src/i2code/implement/implement_opts.py:66`) already rejects `--trunk` with `--isolate`, `--address-review-comments` and the other worktree-only options, so no `--thread`-specific check is needed for them.
- Q1's goal still holds: the user runs one thread on the current branch, reviews the commits, then runs the next thread.

## Default assumptions

These follow from the answers above and can be changed later.

- **Mode check:** `--thread` without `--trunk` exits with a usage error that says `--thread` requires `--trunk`.
- **Thread already complete:** when thread N has no incomplete tasks, i2code prints that thread N is already complete and exits with status 0.
- **Thread does not exist:** when N is less than 1 or greater than the number of threads, i2code exits with a usage error naming the valid range.
- **Commit recovery:** trunk mode still runs `commit_if_needed` before the first task, as it does today.
- **Stopping:** after thread N's last task completes, i2code prints that thread N is complete and exits. When later threads remain, it names the next thread to run. When thread N was the last thread with incomplete tasks, it prints "All tasks completed!" as today.
- **Progress messages:** unchanged; trunk mode prints the task description for each attempt.
- **Validation timing:** the mode check, the thread number and the earlier threads are checked before any task runs.

## Classification

**Type:** C. Platform/infrastructure capability

**Rationale:** The idea adds an option to the `i2code implement` CLI, a developer workflow tool. Its consumers are developers driving the idea-to-code workflow, not end users of an application, and the specification needs to define the option's contract: how it selects tasks, how it validates input, and how it interacts with the other implement options and modes.

## Closing question: Are there any additional requirements or concerns before creating the specification?

**Answer:** Implement `--thread` for trunk mode only and reject it for other modes (recorded as Q7).
