# Discussion: checking-completed-tasks

## Bug context (from codebase analysis)

The `i2code go` orchestrator prints a misleading "Plan has uncompleted tasks"
banner after a successful worktree+PR implementation run.

- `src/i2code/go_cmd/orchestrator.py:414` — `_check_plan_completion()` runs after
  `i2code implement` returns 0. It calls `self._project.get_next_task()`, which
  reads the plan file in the **main worktree's** idea directory
  (`IdeaProject.plan_file` at `src/i2code/implement/idea_project.py:31`).
- `src/i2code/implement/worktree_mode.py:154` — when the implement command runs
  in worktree+PR mode it marks task checkboxes via `self._work_project`, i.e.
  the **worktree's** copy of the plan file. The main repo's copy is never
  modified during the implement run.
- Result: after `WorktreeMode` reports "All tasks completed!" and marks the PR
  ready (`worktree_mode.py:185-194`), control returns to the orchestrator. The
  orchestrator then reads the stale main-repo plan file, finds the original
  unchecked checkboxes, and prints "Plan has uncompleted tasks".

Implementation modes (`src/i2code/go_cmd/implement_config.py:5-9`):
- `interactive` / `non-interactive`
- isolation: `none` / `nono` / `container` / `vm`
- when isolation is `none`, branch mode is `Worktree (branch + PR)` or
  `Trunk (current branch, no PR)`
- Any isolation other than `none` also implies a worktree
  (`implement_config.py:64-71`)

So "PR-based" effectively means: any config where `trunk` is `false`. In that
case the plan-file edits happen in a worktree path that the orchestrator
doesn't read.

## Questions and answers

### Q1: Source of truth for completion in PR-based modes

In worktree/PR-based implementation modes, what should the orchestrator use as
the source of truth when deciding whether the plan is complete?

**A1:** Check the local directory, i.e. the worktree or clone-of-worktree where
the implement run actually edited files. Open question: how does this interact
with isolation modes (nono / container / VM)?

### Q2: Handling VM-isolation mode

For VM-isolation mode the host has no fresh copy of the plan file (Lima VM
clones internally and pushes to GitHub without a host bind-mount). How should
that case be handled given the "prefer local" preference?

**A2:** Fetch from the PR branch via `gh` (e.g., `gh api` for the plan file at
the PR's head, or `git fetch` + read). Other modes still use the host-local
plan file.

### Q3: Missing host-local plan file

For worktree/nono/container modes, what should happen if the expected host-local
plan file is missing?

**A3:** Not a concern. Assume the worktree/clone exists right after a
successful implement run. No fallback logic until a real bug shows up.

### Q4: Fix scope

Local plan staleness affects more than the orchestrator banner — e.g.,
`state_cmd._has_fully_completed_plan` (`src/i2code/idea_cmd/state_cmd.py:89-95`)
also reads the local plan file. What scope should this fix cover?

**A4:** Just the banner. Fix only `orchestrator._check_plan_completion`. Other
readers of the local plan file are out of scope.

## Classification

**A. User-facing feature** — specifically, a defect fix in the developer-facing
`i2code go` CLI. The orchestrator's misleading completion banner is something
the human developer sees and reacts to (it offers them a follow-up menu of
no-longer-applicable actions). The change is mechanical and contained to one
helper plus per-mode plan-file resolution; it doesn't validate an architectural
concern (B), add a platform capability (C), or serve as a teaching artefact (D).

Rationale for not picking C (platform capability): although `i2code` *is* the
platform here, this work isn't adding a new capability — it's correcting the
behaviour of an existing user-visible workflow step.

### Mode mechanics (from codebase analysis)

Reference: `src/i2code/implement/git_repository.py:140-189`,
`src/i2code/implement/implement_command.py:66-118`,
`src/i2code/implement/isolate_mode.py:60-102`.

- **trunk mode**: `work_project = self.project`. Plan edits land in the main
  repo's idea directory — the current orchestrator check works.
- **worktree mode (no isolation)**: a sibling worktree is created at
  `<parent>/<repo_basename>-wt-<idea_name>`. Plan edits land at
  `<worktree>/<idea_relpath>/<name>-plan.md`. Path is deterministic and the
  orchestrator could derive it.
- **isolation mode (nono / container / VM)**: `IsolateMode` creates a worktree,
  then a clone at `<parent>/<repo_basename>-cl-<idea_name>`, then runs
  `isolarium ... -- i2code implement --isolated` with `cwd=clone_dir`
  (`isolate_mode.py:96-107`). The clone's origin is the GitHub remote.

  How the isolated process sees the clone directory depends on the backend
  (per `~/src/isolarium/README.md` and source):

  - **nono**: command runs on the host with syscall-level sandboxing. The
    host's clone directory IS the agent's working tree (read-write). After the
    run, **the host's clone directory has the latest plan file**.
  - **container (Docker)**: the host's clone directory is bind-mounted into
    the container at `~/repo`
    (`internal/docker/docker.go:63`). Edits in the container land on the
    host's clone directory via the mount. After the run, **the host's clone
    directory has the latest plan file**.
  - **VM (Lima)**: isolarium clones the repo *inside* the VM at `~/repo`
    using a GitHub URL (`internal/lima/clone.go`). The VM has no host
    filesystem mounts. The agent commits and pushes to GitHub from inside
    the VM. **The host's clone directory is NOT updated by the run** — the
    only authoritative source is the PR branch on GitHub.
