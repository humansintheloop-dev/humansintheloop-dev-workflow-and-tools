# Idea: checking-completed-tasks

## Problem

After `i2code go` runs `i2code implement` in a PR-based mode (worktree, or any
isolation mode), the orchestrator prints a misleading completion banner:

```
All tasks completed!
PR marked ready for review
PR: https://github.com/<org>/<repo>/pull/<n>

================================================
  Plan has uncompleted tasks
================================================

<idea>: Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Revise implement options
  3) Commit changes [default]
  4) Implement the entire plan: i2code implement --non-interactive
  5) Exit
```

The "Plan has uncompleted tasks" banner contradicts the success messages that
preceded it, and the follow-up menu offers actions (revise / re-implement) that
make no sense for a completed plan.

## Root cause

`src/i2code/go_cmd/orchestrator.py:414-429` (`_check_plan_completion`) reads
the plan file at `IdeaProject.plan_file` — which resolves to the main repo's
idea directory (`src/i2code/implement/idea_project.py:31`). In PR-based modes
the task checkboxes were updated in a different location:

- worktree (no isolation): `<parent>/<repo>-wt-<idea>/<idea-relpath>/<name>-plan.md`
- isolation = nono: edits on host's clone at `<parent>/<repo>-cl-<idea>/...`
- isolation = container: edits on host's clone via bind-mount
- isolation = VM (Lima): edits inside the VM; no host copy reflects them

The main repo's plan file is never touched during the run, so the orchestrator's
recheck sees the original unchecked boxes and prints the wrong banner.

## Refined idea

Fix `_check_plan_completion` so that, when `i2code implement` exits 0, the
completion check reads the plan file from the *actual* location where the
implement run made its edits. Prefer the host-local copy whenever one exists.

Per-mode source of truth:

| Mode | What to read |
|---|---|
| trunk | main repo's `<idea-dir>/<name>-plan.md` (unchanged) |
| worktree (no isolation) | `<parent>/<repo>-wt-<idea>/<idea-relpath>/<name>-plan.md` |
| isolation = nono | `<parent>/<repo>-cl-<idea>/<idea-relpath>/<name>-plan.md` |
| isolation = container | `<parent>/<repo>-cl-<idea>/<idea-relpath>/<name>-plan.md` |
| isolation = VM | fetch plan file from the PR branch via `gh` (no host copy) |

Worktree/clone path conventions are already centralised in
`GitRepository._sibling_path` (`src/i2code/implement/git_repository.py:140-144`)
and `IdeaProject.worktree_idea_project`
(`src/i2code/implement/idea_project.py:127-130`), so the resolution can reuse
existing helpers.

## Scope

In scope:
- `orchestrator._check_plan_completion` chooses the right plan-file source
  based on the implement config (`trunk` flag and `isolation_type`).
- VM-mode fallback: query the PR branch via `gh`.

Out of scope:
- Other readers of the local plan file (e.g.,
  `state_cmd._has_fully_completed_plan`) — tracked separately if needed.
- Syncing the local plan file back from the worktree/clone.
- Handling the case where the worktree/clone directory has been cleaned up.

## Expected outcome

After a successful PR-based implement run that completed every task, the
orchestrator prints:

```
================================================
  Workflow Complete!
================================================
```

and exits 0 — matching the existing trunk-mode behaviour at
`orchestrator.py:424-429`. The misleading "Plan has uncompleted tasks" banner
no longer appears in this case.
