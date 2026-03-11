# Discussion: implement-loads-env-local

## Context from codebase analysis

- `i2code implement` has three execution modes: **trunk**, **worktree**, and **isolate**.
- **IsolateMode** already handles `.env.local`: it finds it in the main repo and passes `--env-file` to isolarium (line 141-143 in `isolate_mode.py`).
- **WorktreeMode** does NOT load `.env.local`. Worktrees are created via `git worktree add`, which doesn't copy non-tracked files. Since `.env.local` is in `.gitignore`, worktrees lack it.
- **TrunkMode** runs in the main repo directory, so `.env.local` is already present — but it's not loaded into the Python process environment.
- The test script (`test-i2code-implement.sh:320`) symlinks `.env.local` into clone dirs manually.
- `python-dotenv` is NOT currently a dependency.

## Questions and Answers

### Q1: Which execution modes need `.env.local` loading?

**Options:**
- A. Only worktree mode
- B. Both worktree and trunk modes
- C. All three modes (worktree, trunk, and isolate)

**Answer:** C — All three modes. Even though isolate mode already passes `--env-file` to isolarium, the env vars should be loaded consistently across all modes.

### Q2: Where should `.env.local` be resolved from?

**Options:**
- A. Always from `main_repo_dir` (the original checkout) — ignore any `.env.local` in worktree/clone
- B. Current working directory first, fall back to `main_repo_dir` if not found
- C. Current working directory only — no fallback
- D. Both — merge them (current dir overrides `main_repo_dir` values)

**Answer:** C — Current working directory only, no fallback.

### Q3: How should `.env.local` get into worktree/clone directories?

**Answer:** It doesn't need to. When `i2code implement` runs, it loads `.env.local` from CWD. That's it. No copying, symlinking, or fallback logic. If `.env.local` isn't in CWD, nothing happens.

### Q4: Should existing environment variables be overridden by values in `.env.local`?

**Options:**
- A. `.env.local` values override existing env vars
- B. Existing env vars take precedence (`.env.local` only fills in missing vars)

**Answer:** B — Existing env vars take precedence. This is python-dotenv's default behavior (`override=False`).

### Q5: Behavior when `.env.local` doesn't exist?

**Answer:** `load_dotenv()` returns `False` and silently does nothing. No special handling needed.

## Classification

**Classification:** C — Platform/infrastructure capability

**Rationale:** This is an internal infrastructure concern — ensuring environment variables are available across execution modes. It's not user-facing (no new CLI options or visible behavior change), not an architecture POC, and not educational. It's a platform capability that makes the existing `i2code implement` command work correctly in all contexts.

