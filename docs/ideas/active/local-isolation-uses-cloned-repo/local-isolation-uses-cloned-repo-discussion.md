# Discussion: Local Isolation Uses Cloned Repo

## Classification

**A. User-facing feature** — The developer runs `i2code implement --isolate` and expects the agent to be properly isolated from their main repo. The change is security-motivated: replacing a worktree (shared `.git`) with a clone (independent `.git`).

## Questions and Answers

### Q1: Scope — Which modes are affected?

**Context from code analysis:**

The codebase has three execution modes:
- **TrunkMode**: No isolation, works directly on the current branch
- **IsolateMode**: Scaffolds on the idea branch in the main repo, then delegates to an isolarium VM subprocess
- **WorktreeMode**: Creates a git worktree sibling, runs tasks with PR/CI feedback loop

The idea file's point 5 specifically says "Run isolarium in the clone instead of the worktree," which suggests IsolateMode is the primary target. However, WorktreeMode also suffers from the shared `.git` directory problem since it uses worktrees too.

**Question**: Does this change apply only to IsolateMode (isolarium), or should WorktreeMode also switch from worktree to clone for task execution?

**Answer**: A. IsolateMode only. Isolarium runs in the clone. WorktreeMode keeps using worktrees.

### Q2: Intermediate worktree lifecycle

After cloning, the worktree's only purpose was as a staging area for scaffolding. Keeping it maintains the shared `.git` lock concern, but avoids re-scaffolding on re-runs.

**Question**: After the worktree is cloned, what should happen to the intermediate worktree?

**Answer**: B. Keep it. The clone provides isolation; the worktree sits dormant. Avoids re-scaffolding on re-runs.

### Q3: Re-run behavior when the clone already exists

On re-runs, the `-cl-` clone directory may already exist. The worktree is kept (Q2), and the scaffolding guard file (`.hitl_dev/scaffolding-done`) prevents re-scaffolding.

**Question**: When the clone directory already exists on a re-run, what should happen?

**Answer**: A. Reuse the clone. If the `-cl-` directory exists, skip worktree creation, scaffolding, and cloning. Just run isolarium in the existing clone.

### Q4: Cleanup/teardown

**Question**: When cleanup is triggered, should both the worktree and the clone be removed?

**Answer**: Out of scope. Cleanup is not a concern for this feature. There is an existing `--cleanup` flag in the CLI but it's not relevant to the core isolation change.

### Q5: Classification

**Question**: What type of work is this?

- A. User-facing feature
- B. Architecture POC
- C. Platform/infrastructure capability
- D. Educational/example

**Answer**: A. User-facing feature.

### Q6: User-visible changes and primary goal

**Question**: Beyond fixing the lock file problem, should the user see any new CLI flags, output messages, or behavior changes?

**Answer**: The primary goal is **security isolation** — properly isolating the agent from the main repo. With a worktree, the agent has write access back to the main repo via the shared `.git` directory. A clone is a fully independent git repo with no references to the main repo (after reconfiguring `origin` to point to GitHub instead of the worktree path). No new CLI flags or output messages needed — same interface, stronger isolation.
