# Simplify Worktree Branching - Discussion

## Classification

**A. User-facing feature** — Simplification of the existing `i2code implement` worktree branching model. Rationale: this changes the primary user-facing workflow command, not infrastructure or architecture experimentation.

## Codebase Context (derived from exploration)

### Current Architecture

- Two-level branching scheme:
  - Integration branch: `idea/<name>/integration` — long-lived, accumulates all work
  - Slice branches: `idea/<name>/01-<task-name>` — short-lived, one per PR
- `WorkflowState` (in `<idea>-wt-state.json`) tracks `slice_number` and processed PR feedback IDs
- The stacked PR / slice branch scheme is only partially implemented
- Three execution modes: worktree (default), trunk (`--trunk`), isolate (`--isolate`)

### Key Files Affected

- `src/i2code/implement/git_repository.py` — branch creation (`ensure_integration_branch`, `ensure_slice_branch`)
- `src/i2code/implement/worktree_mode.py` — main task loop
- `src/i2code/implement/branch_lifecycle.py` — rebase, cleanup logic
- `src/i2code/implement/workflow_state.py` — state persistence
- `src/i2code/implement/pr_helpers.py` — PR title/body generation
- `src/i2code/implement/implement_command.py` — mode dispatch

## Discussion

### Q1: Scope of the simplification

**Q:** Which execution modes does this simplification affect?
- A. Worktree mode only (isolate inherits the change since it delegates to worktree mode internally)
- B. Worktree and trunk modes
- C. All three modes
- D. Worktree and isolate, leave trunk unchanged

**A:** A — Worktree mode only. Trunk mode is already simple and stays as-is. Isolate mode inherits the change automatically since it delegates to worktree mode.

### Q2: Branch naming convention

**Q:** With a single branch, what naming convention should be used?
- A. `idea/<name>` — clean and simple
- B. `idea/<name>/main` — keeps namespace for possible sub-branches
- C. `<name>` — flat, no prefix
- D. Keep `idea/<name>/integration` — reuse existing name, just stop creating slice branches

**A:** A — `idea/<name>`. Clean and simple.

### Q3: WorkflowState simplification

**Q:** How should we handle the state file now that `slice_number` is irrelevant?
- A. Keep the state file, drop `slice_number` — remove the field, keep only processed feedback ID lists
- B. Keep the state file, keep `slice_number` hardcoded to 1 — minimal change
- C. Replace with a new state format — redesign to store PR number, branch name, etc.
- D. Eliminate the state file entirely — derive all state from Git/GitHub at runtime

**A:** A — Keep the state file, drop `slice_number`. The processed feedback ID lists are still needed.

### Q4: PR title format

**Q:** What should the PR title format be with a single branch/PR per idea?
- A. `[<idea-name>]` — idea name in brackets
- B. `<idea-name>` — plain idea name
- C. Derive from the idea file — use the first line or heading of the idea markdown
- D. `[WIP] <idea-name>` — WIP prefix while draft

**A:** C — Derive the PR title from the idea file (first line or heading).

### Q5: Dead code removal

**Q:** Should dead code (integration/slice branch methods, rebase logic, slice numbering) be removed as part of this change?
- A. Remove all dead code in the same change — clean break
- B. Remove in a follow-up — keep this change focused on new behavior
- C. Deprecate but keep — in case stacked PR approach is revisited

**A:** A — Remove all dead code in the same change. Clean break.

### Q6: PR body content

**Q:** What should the PR body contain?
- A. Idea file content — full text of the idea markdown
- B. Plan file content — task list for reviewers
- C. Both idea and plan
- D. Minimal — just a link to the idea directory in the repo

**A:** D — Minimal. Just a link to the idea directory.

### Q7: Marking PR ready for review

**Q:** How should "mark ready for review" work when all tasks are completed?
- A. Automatic — `i2code implement` calls `gh pr ready` when all tasks are done
- B. Prompt the user — ask whether to mark ready or leave as draft
- C. Always automatic, with a `--no-ready` flag to opt out
- D. Always automatic, with a `--draft` flag to keep as draft

**A:** A — Automatic. Call `gh pr ready` when all tasks are completed.

### Q8: Existing ideas with state files

**Q:** How should the new code handle old state files that contain `slice_number`?
- A. Silently ignore — read only the fields it needs, drop `slice_number` on next save
- B. Migrate explicitly — detect old format, log a message, rewrite without `slice_number`
- C. Error and require manual cleanup

**A:** A — Silently ignore unknown fields. On next save, `slice_number` is naturally dropped.

