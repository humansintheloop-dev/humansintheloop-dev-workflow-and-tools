# Specification: Local Isolation Uses Cloned Repo

## Purpose and Background

The `i2code implement` command supports an `--isolate` mode that delegates task execution to an isolarium VM. Before delegating, the host creates a git worktree, runs scaffolding in it, and launches the isolarium subprocess with the worktree as its working directory.

Git worktrees share the `.git` directory with the main repository. This means the agent running inside isolarium has write access back to the main repo — it can modify lock files, the index, refs, and other git state. This defeats the purpose of isolation.

This feature replaces the worktree as the agent's working directory with a shallow clone. A clone is a fully independent git repository with its own `.git` directory and no filesystem references to the main repo, providing true security isolation.

## Target Users and Personas

**Developer using `i2code implement --isolate`**: A developer who runs automated plan implementation in an isolated environment. They expect the agent to operate in a sandbox that cannot modify their main working repository.

## Problem Statement and Goals

**Problem**: The agent running in IsolateMode can modify the main repo through the shared `.git` directory of a git worktree. This is a security concern — the main repo should be protected from the agent.

**Goals**:
1. The agent running inside isolarium must not have filesystem access to the main repo's `.git` directory or working tree.
2. The agent must still be able to commit and push to the idea branch on GitHub.
3. The existing scaffolding workflow (host-side, before delegation) continues to work.
4. Re-runs are fast — reuse existing artifacts when possible.

## In-Scope

- Modifying `IsolateMode`'s flow to create a shallow clone after scaffolding and run isolarium in the clone
- Reconfiguring the clone's `origin` remote to point to GitHub (not the local worktree)
- Reusing an existing clone on re-runs

## Out-of-Scope

- Changes to `WorktreeMode` (continues using worktrees)
- Changes to `TrunkMode`
- Cleanup/teardown of the clone or worktree (existing `--cleanup` behavior is not modified)
- New CLI flags or output messages

## High-Level Functional Requirements

### FR-1: Clone creation after scaffolding

After scaffolding completes in the worktree, create a shallow clone of the worktree in a sibling directory. The clone directory uses the naming convention `<repo-name>-cl-<idea-name>` (replacing the `-wt-` infix with `-cl-`).

Example:
- Main repo: `/home/user/my-project/`
- Worktree: `/home/user/my-project-wt-my-feature/`
- Clone: `/home/user/my-project-cl-my-feature/`

### FR-2: Remote reconfiguration

After cloning, reconfigure the clone's `origin` remote URL to point to the GitHub remote (the same URL as the main repo's `origin`), not the local worktree path. The clone tracks the idea branch (`idea/<idea-name>`).

### FR-3: Isolarium runs in the clone

The isolarium subprocess receives the clone directory as its `cwd`, replacing the worktree. The inner command (`i2code implement --isolated`) uses the clone as its working directory.

### FR-4: Worktree is retained

The intermediate worktree remains after cloning. It serves as the scaffolding staging area and avoids re-scaffolding on re-runs.

### FR-5: Re-run reuses existing clone

On re-runs, if the clone directory (`-cl-`) already exists, skip worktree creation, scaffolding, and cloning. Run isolarium directly in the existing clone.

## Security Requirements

### SR-1: No filesystem path from clone to main repo

After remote reconfiguration (FR-2), the clone must contain no references (remote URLs, filesystem paths, symlinks) to the main repo or worktree. The clone's `origin` must point to the GitHub remote URL.

### SR-2: Independent `.git` directory

The clone has its own `.git` directory. Git operations in the clone (commits, index changes, lock files) do not affect the main repo.

## Non-Functional Requirements

### NFR-1: Performance

- Clone creation uses `--depth 1` (shallow clone) to minimize time and disk usage.
- Re-runs skip clone creation entirely when the clone directory exists.

### NFR-2: Compatibility

- The inner command (`i2code implement --isolated`) is unchanged. It receives a different `cwd` (clone instead of worktree) but the directory structure is identical.
- The `worktree_idea_project()` path computation works identically for the clone since it has the same directory layout.

## Success Metrics

1. After clone creation, no file under the clone's `.git/` directory references the main repo path.
2. Isolarium subprocess runs with `cwd` pointing to the clone directory.
3. Commits and pushes from inside isolarium reach GitHub successfully.
4. Re-runs with an existing clone directory skip the clone step and proceed directly to isolarium.

## Epics and User Stories

### Epic: Clone-Based Isolation for IsolateMode

**US-1**: As a developer, when I run `i2code implement --isolate`, the agent operates in a cloned repo that has no filesystem connection to my main repo, so that my main repo is protected from the agent.

**US-2**: As a developer, when I re-run `i2code implement --isolate` after a failure, the existing clone is reused without re-scaffolding, so that re-runs are fast.

## Scenarios

### Scenario 1: First run — clone creation (primary end-to-end scenario)

**Preconditions**: No worktree or clone exists for the idea.

**Flow**:
1. Developer runs `i2code implement --isolate docs/features/my-feature`
2. System creates idea branch `idea/my-feature`
3. System creates worktree at `<repo>-wt-my-feature`
4. System runs scaffolding in the worktree (host-side)
5. System creates shallow clone at `<repo>-cl-my-feature`
6. System reconfigures clone's `origin` to GitHub remote URL
7. System runs isolarium subprocess with `cwd=<repo>-cl-my-feature`
8. Agent inside isolarium works in the clone — all git operations are local to the clone

**Postconditions**: Main repo's `.git` directory is unmodified by the agent. Worktree and clone both exist on disk.

### Scenario 2: Re-run — clone already exists

**Preconditions**: Clone directory `<repo>-cl-my-feature` exists from a previous run.

**Flow**:
1. Developer runs `i2code implement --isolate docs/features/my-feature`
2. System detects clone directory exists
3. System skips worktree creation, scaffolding, and cloning
4. System runs isolarium subprocess with `cwd=<repo>-cl-my-feature`

**Postconditions**: Same as Scenario 1. No re-scaffolding or re-cloning occurs.

### Scenario 3: Scaffolding already done but no clone

**Preconditions**: Worktree exists with scaffolding guard file (`.hitl_dev/scaffolding-done`), but no clone.

**Flow**:
1. Developer runs `i2code implement --isolate docs/features/my-feature`
2. System detects worktree exists (reuses it)
3. Scaffolding guard prevents re-scaffolding
4. System creates shallow clone from the existing worktree
5. System reconfigures clone's `origin` and runs isolarium in the clone

**Postconditions**: Clone created from previously-scaffolded worktree. Agent runs in isolation.

## Constraints and Assumptions

- **Assumption**: Isolarium uses the `cwd` parameter to determine the working directory for the VM. No changes are needed to isolarium itself.
- **Assumption**: The inner command (`i2code implement --isolated`) works identically whether the `cwd` is a worktree or a clone, since the directory structure is the same.
- **Constraint**: The clone's `origin` URL must be obtained from the main repo's `origin` remote configuration.
- **Constraint**: Shallow clone depth is 1 (`--depth 1`). This is sufficient because the idea branch is already pushed to GitHub before cloning, and the agent creates new commits on top.
