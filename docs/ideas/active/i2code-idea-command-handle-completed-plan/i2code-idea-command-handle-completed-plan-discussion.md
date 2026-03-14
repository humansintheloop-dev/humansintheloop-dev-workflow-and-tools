# Discussion: i2code-idea-command-handle-completed-plan

## Context from Codebase Analysis

- Currently, completing all plan tasks does NOT auto-transition the idea state — users must manually run `i2code idea state <name> completed`.
- Transition rules require linear progression: `draft → ready → wip → completed`. Only `wip` ideas can transition to `completed`.
- `i2code idea archive --completed` already bulk-archives ideas in `completed` state, so this feature fills the gap before that step.

## Q1: How should this feature be exposed in the CLI?

**Options considered:**
- A. New option on `idea state` — a flag like `i2code idea state --complete-finished`
- B. New option on `idea archive` — extend `--completed` to also auto-transition before archiving
- C. New subcommand — a dedicated `i2code idea sweep` or similar

**Answer:** A — New option on `idea state`. Add a flag that bulk-transitions all wip ideas with fully-completed plans to `completed` state.

## Q2: What flag name should trigger bulk-completing ideas with finished plans?

**Options considered:**
- A. `--completed-plans` — explicit, transitions wip ideas whose plans have all tasks completed
- B. `--complete-finished` — action-oriented
- C. `--auto` — short and generic

**Answer:** A — `--completed-plans`. Usage: `i2code idea state --completed-plans`

## Q3: Should `--completed-plans` be mutually exclusive with a specific idea name?

**Options considered:**
- A. Bulk-only (no name) — mutually exclusive with `<name>`, scans all active wip ideas. Consistent with `archive --completed`.
- B. Both bulk and single — without a name scans all, with a name checks just that idea.

**Answer:** A — Bulk-only. `--completed-plans` is mutually exclusive with the `<name>` argument, consistent with `archive --completed`.

## Q4: How should git commits work for bulk transitions?

**Options considered:**
- A. Single commit for all — one commit listing all transitioned ideas
- B. One commit per idea — consistent with individual `idea state` transitions

**Answer:** A — Single commit listing all transitioned ideas. Message format: `"Mark ideas with completed plans as completed: idea-a, idea-b, idea-c"`

## Q5: What should happen when no matching ideas are found?

**Options considered:**
- A. Silent success (exit 0) — good for scripting
- B. Informational message — print "No wip ideas with completed plans found" and exit 0

**Answer:** B — Print an informational message and exit 0.

## Q6: Output when ideas are transitioned

**Default assumption (derived from `archive --completed` pattern):**
- Print each transitioned idea name as it's processed (e.g., `"Mark idea idea-a as completed"`)
- Support `--no-commit` flag to stage but not commit, consistent with other `idea state` and `idea archive` commands

## Design Decisions Summary

1. **CLI surface:** New `--completed-plans` flag on `i2code idea state`
2. **Scope:** Only scans active ideas in `wip` state (transition rules require `wip → completed`)
3. **Detection:** Uses `Plan.get_next_task() is None` and plan has at least one task to determine all tasks are complete
4. **Mutual exclusivity:** `--completed-plans` cannot be combined with a `<name>` argument
5. **Git behavior:** Single commit for all transitions
6. **Empty result:** Informational message, exit 0
7. **`--no-commit` support:** Yes, consistent with existing commands

## Classification

**Type: A — User-facing feature**

**Rationale:** This adds a new CLI capability that directly addresses a gap in the user's workflow. Users currently must manually check which ideas have fully-completed plans and transition them one-by-one. This automates that step, fitting naturally between `i2code implement` (which completes plan tasks) and `i2code idea archive --completed` (which archives completed ideas).
