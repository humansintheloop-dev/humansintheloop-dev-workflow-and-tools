# Idea: completed-plan-next-action

## Problem

When `i2code go` detects a plan file exists (`WorkflowState.HAS_PLAN`), it shows
the same menu regardless of whether the plan's tasks are actually done. A user
whose plan is fully checked still sees:

```
<idea>: Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Revise implement options
  3) Commit changes [default]
  4) Implement the entire plan: i2code implement --non-interactive
  5) Exit
```

"Implement the entire plan" makes no sense for a completed plan, and the menu
gives no hint about the actual next step (mark idea completed, merge the PR,
or pull from origin).

The shipped `checking-completed-tasks` idea fixed the *post-implement banner*
but not the *pre-menu detection* — the menu builder at
`_build_has_plan_options` (`src/i2code/go_cmd/orchestrator.py:318`)
unconditionally appends the implement option.

## Goal

When `i2code go` is invoked against an idea whose plan is complete, detect
*where* completion lives and offer the single appropriate next action instead
of the generic HAS_PLAN menu.

Three cases, distinguished by where the completed plan is found:

| Case | Detected by | Next action offered |
|---|---|---|
| 1: local plan complete | parse local plan, `get_next_task() is None` | Mark idea `wip → completed` |
| 2: open PR has complete plan | local incomplete + open PR exists for `idea/<name>` + plan on PR branch complete | Open PR in browser (`gh pr view --web`) |
| 3: origin's current branch has complete plan | local incomplete + origin/`<current-branch>` plan complete | `git pull` |

Detection should short-circuit on the cheapest source: read the local plan
first and only make `gh` calls when the local view says "not done." When a
remote check fails (offline, no `gh`, rate limit), fall back to today's menu
rather than hiding options.

## Locations

**Menu builder (primary change site)**
- `src/i2code/go_cmd/orchestrator.py:318` — `_build_has_plan_options` needs
  to consult completion state before appending `IMPLEMENT_PLAN`.
- `src/i2code/go_cmd/orchestrator.py:268` — `_dispatch_has_plan` needs new
  branches for the three case-specific actions.
- `src/i2code/go_cmd/orchestrator.py:280` — `_handle_has_plan_choice` needs
  handlers for "mark complete", "open PR", and "git pull".

**Reusable helpers (already exist)**
- `src/i2code/go_cmd/plan_completion.py:125` — `resolve_plan_text` already
  reads the plan from worktree/clone/PR for case 1 in PR-based modes.
- `src/i2code/go_cmd/plan_completion.py:56` — `derive_origin_owner_repo`
  parses the origin URL for `gh api` calls.
- `src/i2code/go_cmd/plan_completion.py:78` — `_read_vm_plan_text` shows
  the pattern for fetching plan text by `ref=<branch>` — case 3 retargets
  this at `<current-branch>` instead of `idea/<name>`.
- `src/i2code/idea_cmd/state_cmd.py` — `execute_transition` performs
  the `wip → completed` move for case 1's action.
- `src/i2code/plan_domain/parser.py` — `parse(plan_text).get_next_task()`
  is the completion predicate.

**New detection needed**
- Case 2 disambiguation: `gh pr list --head idea/<name> --state open` to
  distinguish "open PR exists" from "PR was already merged/closed."
- Case 3: `gh api repos/<owner>/<repo>/contents/<plan-path>?ref=<current-branch>`
  where `<current-branch>` comes from `git rev-parse --abbrev-ref HEAD`.

**Unchanged (out of scope)**
- `_check_plan_completion` at `src/i2code/go_cmd/orchestrator.py:419` —
  the post-implement banner stays as-is; folding it into the new pre-menu
  detection is a follow-up simplification, not part of this idea.
- `_has_fully_completed_plan` at `src/i2code/idea_cmd/state_cmd.py:89` —
  same blind-spot as the original orchestrator bug, but tracked separately
  (called out as out-of-scope in `checking-completed-tasks` too).
- Existing menu options for `draft`/`ready` lifecycle states — this idea
  only changes the `wip` + HAS_PLAN intersection.
