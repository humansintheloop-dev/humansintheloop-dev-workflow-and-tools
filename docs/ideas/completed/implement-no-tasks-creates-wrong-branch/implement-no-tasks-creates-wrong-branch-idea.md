`i2code implement` creates a new slice branch when all tasks are complete, resetting the worktree.

# Bug

`_worktree_mode()` in `implement_command.py` derives the slice branch name from `get_next_task()`:

```python
next_task = self.project.get_next_task()
first_task_name = next_task.task.title if next_task else "implementation"
```

When all tasks are complete, `get_next_task()` returns `None` and `first_task_name` falls back to `"implementation"`. This generates a slice branch name like `idea/<name>/01-implementation` which doesn't match the existing slice branch (e.g. `idea/<name>/01-has-plan-menu-shows-...`).

`ensure_slice_branch` creates this new branch from the integration branch (which points to the initial commit), and `checkout` switches the worktree to it — effectively resetting the worktree back to the beginning.

# How it was discovered

Ran `i2code implement` on a completed idea (`i2code-go-commit-uncommitted-changes-before-implement`). The worktree was switched from the working branch (at `3f61000` with 4 implementation commits) to a new empty branch at `1eb7b1b` (the initial commit).

The reflog confirmed:
```
16:33:50 checkout: moving from .../01-has-plan-menu-shows-... to .../01-implementation
```

No work was lost — the original branch still exists — but the worktree now points to a blank branch.

# Fix

1. Write a failing test that reproduces the bug: `_worktree_mode()` called when all tasks are complete should exit with an error message, not create branches or touch the worktree.
2. `_worktree_mode()` should call `get_next_task()` early and exit with an error message if it returns `None` — before creating branches or touching the worktree.

# Future improvement

Once this bug is fixed, add an earlier check in `ImplementCommand.execute()` for incomplete tasks. Note: this check might produce false positives if the main repo isn't up to date (PR not merged, changes not pulled, etc.), so the `_worktree_mode()` guard is the essential fix.

# Key files

- `src/i2code/implement/implement_command.py:82-112` — `_worktree_mode()`
- `src/i2code/implement/git_repository.py:112-126` — `ensure_slice_branch()`
