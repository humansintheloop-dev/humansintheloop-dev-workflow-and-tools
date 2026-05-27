# Spec: checking-completed-tasks

Type: **User-facing feature** (defect fix in the `i2code go` CLI).

## Purpose and background

`i2code go` orchestrates the idea → spec → plan → implement workflow. After the
embedded `i2code implement` subprocess exits 0, the orchestrator does a
post-run "is the plan complete?" check and prints one of two banners:

- "Workflow Complete!" + `sys.exit(0)` — if no task remains
- "Plan has uncompleted tasks" + redisplays the workflow menu — otherwise

The check at `src/i2code/go_cmd/orchestrator.py:414-429` reads the plan file at
`IdeaProject.plan_file` (`src/i2code/implement/idea_project.py:31`), which
always points at the **main repo's** idea directory.

In any PR-based implement mode the implement subprocess edits a **different**
copy of the plan file:

| Mode | Where plan-file edits happen |
|---|---|
| trunk (`trunk=true`, `isolation=none`) | main repo's idea directory |
| worktree (`trunk=false`, `isolation=none`) | sibling worktree `<parent>/<repo>-wt-<idea>/<idea-relpath>/` |
| isolation = nono | host clone `<parent>/<repo>-cl-<idea>/<idea-relpath>/` (syscall sandbox runs on host) |
| isolation = container | host clone `<parent>/<repo>-cl-<idea>/<idea-relpath>/` (bind-mounted into Docker at `~/repo`) |
| isolation = vm | inside the Lima VM at `~/repo`; pushed to GitHub; **no host copy** |

Because the main repo's plan file is never touched during a PR-based run, the
orchestrator's recheck always reports the original unchecked boxes and prints
the "Plan has uncompleted tasks" banner — even when the implement subprocess
just announced "All tasks completed!" and marked the PR ready for review. The
user is then dropped back into a menu offering revise / re-implement actions
that no longer apply.

## Target user and persona

**The idea author** — a developer using `i2code go` on their own machine to
take an idea from brainstorm through implementation. Single persona: there is
no multi-user authorization model.

## Problem statement and goals

**Problem:** `i2code go`'s post-run completion banner contradicts the
implement subprocess's own success messaging in every PR-based mode, and
follows that contradiction with an irrelevant menu.

**Goals:**

1. When the implement subprocess exits 0 *and* every plan task is in fact
   marked complete, the orchestrator prints `Workflow Complete!` and exits 0
   — regardless of which implement mode was used.
2. When the implement subprocess exits 0 *and* tasks remain unchecked, the
   orchestrator still prints `Plan has uncompleted tasks` and shows the
   workflow menu — regardless of mode.
3. The check reads the plan file from the location where the implement
   subprocess actually edited it.

## In scope

- A single change to the orchestrator's post-run completion check
  (`_check_plan_completion`) so that it resolves the plan-file path based on
  the implement configuration (`trunk` flag plus `isolation_type` from
  `<idea-dir>/<idea-name>-implement-config.yaml`).
- VM-mode fallback that fetches the plan file from the PR branch via the `gh`
  CLI when no host-local copy exists.
- Reusing existing helpers (`GitRepository._sibling_path`,
  `IdeaProject.worktree_idea_project`) rather than duplicating path
  conventions.

## Out of scope

- Other readers of the local plan file. In particular,
  `state_cmd._has_fully_completed_plan` (`src/i2code/idea_cmd/state_cmd.py:89-95`)
  still reads the main repo's plan file. That staleness is real but tracked
  separately.
- Syncing the local plan file back from the worktree/clone after a successful
  run.
- Handling cleanup of the worktree/clone directory between the implement run
  and the orchestrator's recheck. Per discussion Q3, this is assumed not to
  happen.
- Any changes to `i2code implement` itself, to `WorktreeMode`, or to
  `IsolateMode`.
- Any changes to the implement-config schema or wizard.

## Functional requirements

### FR1. Per-mode plan-file resolution

`_check_plan_completion` must derive the plan-file path from the implement
config persisted at `<idea-dir>/<idea-name>-implement-config.yaml` (read by
`read_implement_config` at `src/i2code/go_cmd/implement_config.py:12-38`). The
mapping is:

| `trunk` | `isolation_type` | Plan-file source |
|---|---|---|
| `true` | `none` | `<idea-dir>/<idea-name>-plan.md` (main repo — unchanged) |
| `false` | `none` | `<sibling>/<repo>-wt-<idea>/<idea-relpath>/<idea-name>-plan.md` |
| `false` | `nono` | `<sibling>/<repo>-cl-<idea>/<idea-relpath>/<idea-name>-plan.md` |
| `false` | `container` | `<sibling>/<repo>-cl-<idea>/<idea-relpath>/<idea-name>-plan.md` |
| `false` | `vm` | plan file fetched from PR branch `idea/<idea-name>` via `gh` |

Where:

- `<sibling>` = parent directory of the main repo root (matches
  `GitRepository._sibling_path` at `src/i2code/implement/git_repository.py:140-144`).
- `<repo>` = basename of the main repo root.
- `<idea-relpath>` = `os.path.relpath(idea_dir, main_repo_root)` (matches
  `IdeaProject.worktree_idea_project` at
  `src/i2code/implement/idea_project.py:127-130`).

The config file is the single source of truth. If the implement-config file is
missing (e.g., user invoked `i2code implement` manually with overrides), fall
back to today's behaviour: read the main repo's plan file.

### FR2. Local plan-file completion check (trunk / worktree / nono / container)

For all modes except VM, the orchestrator:

1. Resolves the plan-file path per FR1.
2. Parses it with the same machinery used today (`with_plan_file` →
   `plan.get_next_task()`).
3. If `get_next_task()` is `None`, prints `Workflow Complete!` and exits 0
   (matches existing trunk-mode behaviour at
   `src/i2code/go_cmd/orchestrator.py:424-429`).
4. Otherwise, prints `Plan has uncompleted tasks` and returns, allowing the
   orchestrator's main loop to redisplay the menu.

Per discussion Q3, no fallback is provided if the expected host-local file is
missing. The orchestrator may raise its existing error path or surface a
`FileNotFoundError` to the user — this is acceptable.

### FR3. VM-mode plan-file fetch via gh

For VM mode (`trunk=false`, `isolation_type=vm`), the orchestrator:

1. Resolves the PR branch name: `idea/<idea-name>` (matches
   `GitRepository.ensure_idea_branch` at
   `src/i2code/implement/git_repository.py:133`).
2. Resolves the in-repo plan-file path:
   `<idea-relpath>/<idea-name>-plan.md`.
3. Resolves the GitHub `<owner>/<repo>` from the main repo's `origin` remote.
4. Fetches the plan file's raw contents via:
   `gh api "repos/<owner>/<repo>/contents/<idea-relpath>/<idea-name>-plan.md?ref=idea/<idea-name>" -H "Accept: application/vnd.github.raw"`.
5. Parses the returned text with the same plan parser used elsewhere.
6. Applies the same banner logic as FR2 steps 3–4.

If the `gh` call fails for any reason (network, auth, missing branch, missing
file), the orchestrator prints a single diagnostic line of the form
`Could not check plan completion: <reason>` and returns without printing
either completion banner. The implement subprocess's own success messages
remain authoritative for the user.

### FR4. No change to trunk-mode behaviour

When `trunk=true` and `isolation_type=none`, the resolved plan-file path is
identical to today's `IdeaProject.plan_file`. The user must observe no
behavioural change in that mode.

## Security requirements

This is a single-user, local CLI tool. There are no endpoints, no roles, and
no authorization decisions introduced by this change.

The only new external interaction is the `gh` CLI call in FR3:

- **Identity / authorization:** the call runs as the user's local `gh` session
  and inherits whatever scopes the user has already authorised. The change
  introduces no new credential storage, no new token handling, and no new
  privileges.
- **Network exposure:** the call is read-only (`GET .../contents/...`) and
  targets the same repository the user is already operating against.
- **Failure handling:** when `gh` is unavailable or unauthenticated, FR3's
  fallback ensures the orchestrator degrades gracefully (one diagnostic line,
  no banner) rather than leaking error detail or crashing.

## Non-functional requirements

- **Latency (non-VM modes):** the check must remain a local file read — no
  noticeable change relative to today's behaviour.
- **Latency (VM mode):** one `gh api` round-trip is acceptable. Target: under
  ~3 s on a typical broadband connection.
- **UX consistency:** the success message stays exactly
  `Workflow Complete!` and the failure message stays exactly
  `Plan has uncompleted tasks`. Banner formatting (the `=` rule lines, blank
  lines, indentation) is unchanged.
- **Exit semantics:** completion still causes `sys.exit(0)` and the menu still
  reappears on incompleteness. The orchestrator's surrounding control flow
  must not change.
- **Reliability:** the fix must not regress trunk mode, which is exercised by
  existing tests (`tests/go-cmd/` and related).
- **Discoverability:** no new user-facing config, flags, or environment
  variables are introduced.

## Success metrics

1. Running `i2code go` to completion in worktree+PR mode (the path that
   triggered this idea) prints `Workflow Complete!` and exits 0, with no
   `Plan has uncompleted tasks` banner in the same session.
2. Running `i2code go` to completion in each isolation mode (nono, container,
   vm) prints `Workflow Complete!` and exits 0.
3. Running `i2code go` in trunk mode shows identical output to today
   (regression check).
4. The unit tests covering `_check_plan_completion` pass for every (trunk,
   isolation_type) pair.

## Epics and user stories

### Epic 1: Per-mode completion check

- **US-1.1 — trunk regression guard.** As the idea author running `i2code go`
  in trunk mode, when the implement subprocess completes every task, I see
  `Workflow Complete!` and the command exits 0 — exactly as it does today.
- **US-1.2 — worktree completion.** As the idea author running `i2code go` in
  worktree+PR mode, when the implement subprocess marks every task complete in
  the worktree's plan file, I see `Workflow Complete!` and the command exits
  0, without the `Plan has uncompleted tasks` banner appearing.
- **US-1.3 — nono completion.** Same as US-1.2 but with `isolation_type=nono`;
  the check reads the host clone directory's plan file.
- **US-1.4 — container completion.** Same as US-1.2 but with
  `isolation_type=container`; the check reads the host clone directory's plan
  file (populated via Docker bind-mount).
- **US-1.5 — incomplete plan still flagged.** As the idea author, if my
  implement run exits 0 but some tasks were not marked complete in whichever
  plan-file copy was edited, I still see `Plan has uncompleted tasks` and the
  workflow menu, so I can take corrective action.

### Epic 2: VM-mode remote completion check

- **US-2.1 — VM completion via gh.** As the idea author running `i2code go`
  with `isolation_type=vm`, when the VM has pushed all task completions to
  the PR branch, I see `Workflow Complete!` and the command exits 0.
- **US-2.2 — VM gh failure is graceful.** As the idea author running with
  `isolation_type=vm`, if the `gh` CLI is unavailable, unauthenticated, or
  the PR branch is missing, the orchestrator prints a single
  `Could not check plan completion: <reason>` line and returns without
  showing a banner — the implement subprocess's own `All tasks completed!` /
  `PR marked ready for review` lines remain on screen as my source of truth.

## Scenarios (for later steel-thread planning)

The primary end-to-end scenario is **Scenario S1** below. The other scenarios
are companion paths the implementation must support; they are listed here to
inform later planning, not to be implemented as separate threads.

### S1 (primary). Worktree+PR run completes cleanly

1. The user has an idea directory under `docs/ideas/active/<name>/` containing
   `<name>-idea.md`, `<name>-spec.md`, `<name>-plan.md`, and an
   implement-config file with `trunk: false`, `isolation_type: none`.
2. The user runs `i2code go <name>` and chooses the implement option.
3. The implement subprocess runs in the sibling worktree
   `<parent>/<repo>-wt-<name>/`, marks every task checkbox complete in the
   worktree's plan file, opens (or reuses) the PR, marks it ready for review,
   and exits 0.
4. Control returns to the orchestrator's `_check_plan_completion`.
5. The orchestrator resolves the worktree plan-file path:
   `<parent>/<repo>-wt-<name>/<idea-relpath>/<name>-plan.md`.
6. It parses that file and finds no remaining tasks.
7. It prints the `Workflow Complete!` banner and `sys.exit(0)`.
8. The user does **not** see `Plan has uncompleted tasks` and is **not**
   redropped into the workflow menu.

### S2. Trunk-mode run completes cleanly (regression guard)

1. Same prerequisites as S1 but the implement-config has `trunk: true`,
   `isolation_type: none`.
2. The implement subprocess edits the main repo's plan file directly.
3. The orchestrator's resolution returns the main repo's plan file
   (unchanged from today).
4. The user sees `Workflow Complete!` and the command exits 0 — output
   indistinguishable from today's.

### S3. Container-isolation run completes cleanly

1. Implement-config has `trunk: false`, `isolation_type: container`.
2. The implement subprocess runs inside Docker; the host's clone directory
   `<parent>/<repo>-cl-<name>/` is bind-mounted as `~/repo` and
   receives the plan-file edits.
3. The orchestrator resolves the clone-path plan file and reads it from the
   host filesystem.
4. The user sees `Workflow Complete!` and exits 0.

### S4. Nono-isolation run completes cleanly

Equivalent to S3 with `isolation_type: nono`. The nono sandbox runs the agent
on the host with syscall-level restrictions, so the same host clone path
contains the completed plan file.

### S5. VM-isolation run completes cleanly

1. Implement-config has `trunk: false`, `isolation_type: vm`.
2. The Lima VM clones the repo internally, runs the implement loop, and
   pushes task completions to the PR branch `idea/<name>` on GitHub.
3. The orchestrator detects VM mode and issues
   `gh api repos/<owner>/<repo>/contents/<idea-relpath>/<name>-plan.md?ref=idea/<name>`
   with `Accept: application/vnd.github.raw`.
4. It parses the returned text and finds no remaining tasks.
5. The user sees `Workflow Complete!` and the command exits 0.

### S6. PR-based run with some tasks still incomplete

1. Any PR-based mode. The implement subprocess exits 0 (its own checks passed
   for the tasks it attempted) but one or more checkboxes remain unchecked in
   the authoritative plan-file copy (worktree / clone / PR branch).
2. The orchestrator's check finds a next task.
3. The user sees `Plan has uncompleted tasks` and the workflow menu.

### S7. VM-mode check cannot reach GitHub

1. Implement-config has `isolation_type: vm`.
2. The `gh api` call fails (no auth, no network, missing branch, missing
   file).
3. The orchestrator prints
   `Could not check plan completion: <reason>` (single line, no banner) and
   returns control to its main loop.
4. The implement subprocess's earlier `All tasks completed!` /
   `PR marked ready for review` / PR URL lines remain on screen and act as
   the user's signal.

### S8. Implement-config file is missing

1. The user invoked `i2code go` against an idea whose
   `<name>-implement-config.yaml` is absent (e.g., earlier runs predate the
   config feature, or it was deleted).
2. `read_implement_config` returns `None`.
3. The orchestrator falls back to today's behaviour: read the main repo's
   plan file. This preserves backward compatibility and is identical to
   trunk mode for the purposes of this check.

## Constraints and assumptions

- The implement-config file is the authoritative record of which mode the
  implement subprocess used. The orchestrator does not need to inspect
  process arguments, environment, or filesystem heuristics to determine mode.
- Worktree/clone path conventions are stable and centralised in
  `GitRepository._sibling_path` and `IdeaProject.worktree_idea_project`.
  Reusing these helpers (rather than re-implementing the convention) is a
  hard requirement so that path drift cannot decouple the resolver from the
  rest of the system.
- The idea branch name is always `idea/<idea-name>` (`ensure_idea_branch`).
- The `gh` CLI is available on the user's machine in VM mode — it is already
  a prerequisite of the existing implement workflow.
- Worktree/clone directories exist on disk at the moment the orchestrator
  runs its post-implement check (discussion Q3).
- The change does not need to handle parallel `i2code go` invocations on the
  same idea; sibling paths are deterministic by idea name and concurrent runs
  are out of scope.
