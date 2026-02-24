# Simplify Worktree Branching

The current scheme of a worktree using stacked PRs/slice branches is too complicated and isn't fully implemented. Replace the two-level branching model (integration branch + slice branches) with a single branch per idea.

## Simplified Flow

1. `i2code implement` (worktree mode) creates a single branch `idea/<name>` and ensures the worktree exists.
2. The task implementation loop works as before: pushing commits, creating a draft PR after the first push, checking the PR for feedback, checking GitHub Actions workflows, etc.
3. When all tasks have been completed, the PR is automatically marked ready for review via `gh pr ready`.

## Key Decisions

- **Scope**: Worktree mode only. Trunk mode is already simple and stays as-is. Isolate mode inherits the change since it delegates to worktree mode.
- **Branch naming**: `idea/<name>` — single branch, no integration/slice split.
- **PR title**: Derived from the idea file (first line or heading).
- **PR body**: Minimal — just a link to the idea directory in the repo.
- **State file**: Keep `<idea>-wt-state.json` but drop `slice_number`. Retain processed feedback ID lists. Silently ignore `slice_number` in old state files.
- **Dead code**: Remove all dead code (integration/slice branch methods, rebase logic, slice numbering) in the same change.
- **Ready for review**: Automatically call `gh pr ready` when all tasks complete.
