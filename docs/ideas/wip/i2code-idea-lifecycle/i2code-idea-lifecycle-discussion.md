# i2code idea lifecycle — Discussion

## Classification

**Type:** A. User-facing feature

**Rationale:** This adds new CLI subcommands (`idea list`, `idea move`) and modifies the user-facing `i2code go` workflow with automatic state transition prompts. The feature is entirely about the developer's interaction with the idea lifecycle through the CLI.

## Codebase Context (derived from code analysis)

- Ideas live in `docs/ideas/{draft,ready,wip,completed,abandoned}/<name>/`
- `IdeaProject` (value object) derives file paths from a directory — it does NOT currently track which state directory the idea is in
- The `go` orchestrator detects workflow state from **file existence** (idea, spec, plan files), not from the **directory state** (draft/ready/wip)
- There is no existing `idea list` or `idea move` command
- `i2code idea brainstorm` creates ideas directly in a user-specified directory
- The `write-idea` skill always creates ideas in `docs/ideas/draft/`

## Questions and Answers

### Q1: Should `i2code go` handle end-of-lifecycle transitions (wip → completed, wip → abandoned)?

**Answer:** C — No. `go` only handles `draft → ready` and `ready → wip`. Both `completed` and `abandoned` are manual `idea move` operations.

**Implication:** The orchestrator's state transition responsibility is limited to the "forward progress" path leading into implementation. Post-implementation lifecycle management is the user's responsibility via `idea move`.

### Q2: After `go` moves an idea (e.g., draft → wip), the original directory path is invalid. How should `go` handle this?

**Answer:** C — Both. `go` accepts either a name or a path, resolves the current location, and updates its internal `IdeaProject` reference after moves.

**Implications:**
- Need an idea **resolver** that can find an idea by name across all state directories (scan `docs/ideas/{draft,ready,wip,completed,abandoned}/<name>/`)
- `go` and other commands that currently take a directory path should also accept a bare idea name
- After `idea move`, `IdeaProject` must be reconstructed with the new path
- Shell completions should work for both modes: path completion (default shell behavior) and idea name completion (custom completer that scans state directories)

### Q3: Should `idea state` enforce transition rules?

**Answer:** A — Enforce a linear progression with validation.

**Command rename:** `idea move` → `idea state` (e.g., `i2code idea state my-feature ready`)

**Transition rules:**
- `draft → ready` — requires plan file to exist
- `ready → wip` — requires plan file to exist
- `wip → completed` — allowed (no additional artifact check)
- `any → abandoned` — always allowed
- Backward moves (e.g., `wip → draft`) — require `--force` flag
- Skipping states (e.g., `draft → wip`) — require `--force` flag

### Q4: Should `go` prompt or auto-move for state transitions?

**Answer:** B — Prompt for both transitions. Always ask before moving.

**Behavior in `go`:**
- When a plan file exists and idea is in `draft/`: prompt "Move idea to ready?"
- Before calling implement when idea is in `ready/`: prompt "Move idea to wip?"
- If the user declines, continue the workflow without moving (no blocking)

### Q5: What should `idea list` display for each idea?

**Answer:** Alphabetical flat list (not grouped by state) showing name, state, and directory — similar to `git worktree list` output format.

**Example output:**
```
enhance-non-interactive-claude  draft      docs/ideas/draft/enhance-non-interactive-claude
i2code-idea-lifecycle           draft      docs/ideas/draft/i2code-idea-lifecycle
plan-validation-refactor        wip        docs/ideas/wip/plan-validation-refactor
```

**Filtering:** `--state wip` filters to a single state but keeps the same columnar format.

### Q6: Should other commands (`spec create`, `design create`, `brainstorm`) also accept idea names?

**Answer:** B — Only `go` and `idea` subcommands get name resolution for now. Other commands keep the existing directory-path interface. Name resolution for the rest is a future enhancement.

**Implication:** The resolver module should be designed for reuse (not coupled to `go` or `idea_cmd`), so other commands can adopt it later without refactoring.

### Q7: When `go` prompts to move and the user declines, what happens?

**Answer:** A — Continue silently. The user made their choice, just proceed with the workflow. No warnings or reminders.

### Q8: How should state transitions appear in the `go` HAS_PLAN menu?

**Answer:** As a menu option (not a y/N prompt). Revise stays first, the state transition is the second option and the default. The move option only appears when there's a valid forward transition.

**HAS_PLAN menu — idea in `draft/`:**
```
Implementation plan exists. What would you like to do?
  1. Revise the plan
  2. Move idea to ready  [default]
  3. Implement the entire plan
  4. Configure implement options
  5. Exit
```

**HAS_PLAN menu — idea in `ready/`:**
```
Implementation plan exists. What would you like to do?
  1. Revise the plan
  2. Move idea to wip  [default]
  3. Implement the entire plan
  4. Configure implement options
  5. Exit
```

**HAS_PLAN menu — idea already in `wip/`:**
```
Implementation plan exists. What would you like to do?
  1. Revise the plan
  2. Implement the entire plan  [default]
  3. Configure implement options
  4. Exit
```
(No move option; default shifts to Implement)

