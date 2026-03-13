# i2code status command — Discussion

## Classification

**Type: A. User-facing feature**

**Rationale:** This command gives the user visibility into the state of their development workflow — ideas, worktrees, PRs, and remote branches. It is a direct user-facing tool for situational awareness.

## Codebase Context (derived from exploration)

- Features live in `docs/features/<name>/` with files: `*-idea.md`, `*-spec.md`, `*-plan.md`, `*-wt-state.json`
- The existing lifecycle detects states: `no_idea`, `has_idea_no_spec`, `has_spec`, `has_plan`, `complete`
- Worktrees are created as `<repo>-wt-<idea-name>` with branches `idea/<name>/integration` and `idea/<name>/<slice>-<name>`
- State is persisted in `*-wt-state.json` (slice number, processed PR comments/reviews)
- GitHub integration exists via `GitHubClient` for PRs, CI status

## Questions and Answers

### Q1: Scope — global dashboard vs. single-idea status?

**Answer: C — Both.** A global summary by default, with the ability to drill into one idea for detailed status.

### Q2: What information to show in the global summary?

**Answer: C — Rich.** Each idea row shows: idea name, lifecycle state, worktree status, PR status, plan progress (e.g., 3/7 tasks done), and unpulled changes.

### Q3: How to discover which ideas to report on?

**Answer: C — Active ideas only by default.** Show ideas that aren't in `complete` state. A `--all` flag includes completed ones.

### Q4: Worktree/PR detection strategy?

**Answer: A — Convention-only.** Only detect worktrees, branches, and PRs that follow the `idea/<name>/...` naming pattern. Simple and reliable.

### Q5: What does "unpulled changes from origin" mean?

**Answer:** Check if the current local branch is behind its remote tracking branch (e.g., `master` is behind `origin/master`). This is not per-idea — it's a general repo-level check showing whether the user needs to pull.

### Q6: What detail for the single-idea drill-down view?

**Answer: A — Same info as the summary row, but with more readable formatting.** No additional data beyond what the summary shows; just not compressed into a table row.

### Q7: Network access — online or offline?

**Answer: B — Online by default.** Fetch from origin and query GitHub API for PR status. Assume online; fail gracefully if offline.

### Q8: Output format?

**Answer: B — Rich/colored terminal output.** Use a library like `rich` for nicer table rendering with colors.

### Q9: Implementation approach — Python Click command or shell script?

**Answer: A — Python Click command.** Shell scripts are legacy. New module at `src/i2code/status_cmd/`. This gives direct access to `plan_domain`, `GitHubClient`, and `rich`.

### Q10: What PR information to show?

**Answer: C — PR existence + state (open/draft/merged/closed) + CI status (passing/failing/pending).**

### Q11: How to invoke single-idea drill-down?

**Answer: A — By idea name as an argument.** `i2code status <idea-name>`. No argument shows the global summary.

