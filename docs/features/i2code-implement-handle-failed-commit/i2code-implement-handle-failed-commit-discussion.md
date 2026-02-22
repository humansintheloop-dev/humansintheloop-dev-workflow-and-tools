# Discussion: i2code implement — Handle Failed Commit Recovery

## Classification

**Type: A. User-facing feature**

**Rationale:** This changes the observable behavior of the `i2code implement` command by adding recovery logic that users benefit from directly. When a previous run fails to commit, the next run now detects and recovers rather than silently combining tasks.

## Problem Analysis

In `i2code implement`, Claude is responsible for implementing a task, marking it complete in the plan file (`[ ]` → `[x]`), and committing all changes. If the `git commit` fails (e.g., permissions issue), `i2code implement` exits via `sys.exit(1)`, leaving the repo with:

1. Uncommitted plan file changes (task marked `[x]`)
2. Uncommitted implementation changes

On rerun, `get_next_task()` reads the plan file from disk (not from git), sees the task as `[x]`, skips it, and moves to the next task. The result: two tasks' changes get committed together in a single commit.

## Questions and Answers

### Q1: Commit scope for recovery

**Q:** When recovering from a failed commit, should the recovery logic commit all uncommitted changes (plan file + implementation code together), or try to selectively commit only task-related files?

**A:** Commit all uncommitted changes — matches what Claude originally intended to commit. Simple and reliable.

### Q2: Commit message format

**Q:** What commit message format should the recovery commit use?

**A:** Invoke Claude to generate the message. Run Claude (non-interactively) to inspect the uncommitted changes and generate a proper commit message.

### Q3: Recovery flow — who handles the commit

**Q:** Should Claude handle the entire recovery commit (stage + message + commit), or should i2code handle the git operations and only use Claude for the message?

**A:** Claude handles everything — invoke Claude with a prompt to commit all uncommitted changes with an appropriate message. Consistent with existing architecture where Claude owns git operations.

### Q4: Recovery failure handling

**Q:** If the recovery commit via Claude also fails, what should i2code implement do?

**A:** Retry the recovery once. If it still fails, exit with a clear error message.

## Assumptions and Derived Decisions

- **Detection mechanism:** Use `git diff HEAD` on the plan file to check for uncommitted checkbox changes (`[ ]` → `[x]`). Map the diff to an actual task using plan domain logic (`src/i2code/plan_domain/`) to determine whether the task is fully complete.
- **Only recover fully complete tasks:** Recovery commit only happens when the task header itself is `[x]`. If only steps are marked `[x]` but the task header is still `[ ]`, skip recovery — the main loop's `get_next_task()` will return the same task and Claude resumes it naturally.
- **Scope:** Applies to both TrunkMode and WorktreeMode. IsolateMode is excluded since it delegates to a VM and is not affected by local repo state.
- **User notification:** Print an informational message when recovery is detected and attempted (e.g., "Detected uncommitted completed task, attempting to commit...").
- **Placement:** Recovery logic is encapsulated in a `CommitRecovery` class, called from TrunkMode and WorktreeMode. It cannot live before mode dispatch in `ImplementCommand.execute()` because WorktreeMode's uncommitted changes are in the worktree directory, which is set up inside `_worktree_mode()`. TrunkMode calls it at the start of its task loop; WorktreeMode calls it after worktree setup but before the task loop.

### Q5: Partial vs full task completion

**Q:** The diff might show individual steps marked `[x]` without the task itself being complete (interrupted mid-task). Should the recovery use plan domain logic (`src/i2code/plan_domain/`) to determine actual task completion status?

**A:** Yes. Map the diff to an actual task and use plan domain logic to determine whether the task is complete. This handles the case where `i2code implement` failed or was interrupted partway through a task.

### Q6: Handling partial progress

**Q:** When the plan file has uncommitted partial progress (some steps marked `[x]` but task not complete), what should `i2code implement` do?

**A:** Do not commit incomplete work. Skip recovery and let the main loop resume the task. Since `get_next_task()` returns the first task with header `[ ]`, a partially complete task will be picked up again and Claude continues from where it left off.

### Q7: Any additional requirements or concerns?

**Q:** Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?

**A:** No additional requirements. Confirmed that IsolateMode exclusion is correct since it delegates to a VM and is not affected by local repo state.
