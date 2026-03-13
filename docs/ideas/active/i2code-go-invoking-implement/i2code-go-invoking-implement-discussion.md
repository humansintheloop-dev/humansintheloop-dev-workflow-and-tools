# i2code go invoking implement - Discussion

## Classification

**Type:** A. User-facing feature

**Rationale:** This enhances the `i2code go` orchestrator to prompt users for implementation options and persist them, directly improving the developer experience. It adds no new architectural patterns or infrastructure — it wires existing `i2code implement` CLI options into the `i2code go` workflow with user-facing prompts and a config file.

## Current State (from codebase analysis)

- `i2code go` invokes `i2code implement "$dir"` with **zero options** (`idea-to-code.sh:266`)
- `i2code implement` supports many options: `--non-interactive`, `--trunk`, `--isolate`, `--skip-ci-wait`, `--ci-fix-retries`, `--extra-prompt`, etc.
- No YAML config mechanism exists today — the only persisted state is `*-wt-state.json` (worktree workflow state)
- The shell script `idea-to-code.sh` drives the `go` workflow and delegates to `i2code implement` via `run_step`

## Questions and Answers

### Q1: When should the user be prompted for options?

**Answer: C** — On first invocation + a menu option to reconfigure. Save on first run, but add a menu item in the `has_plan` state to change options.

### Q2: Which options should be configurable?

**Answer: A** — Just the two from the idea: interactive vs non-interactive (`--non-interactive`) and worktree vs trunk (`--trunk`).

### Q3: Where should the prompting and config logic live?

**Default assumption: A** — In the shell script (`idea-to-code.sh`). The config is only two flat boolean fields, so simple `grep`/`sed` patterns suffice for YAML parsing. This keeps the shell-based orchestrator self-contained and avoids introducing a new Python subcommand. (Q3 was not explicitly answered; this default was stated during brainstorming and carried forward.)
