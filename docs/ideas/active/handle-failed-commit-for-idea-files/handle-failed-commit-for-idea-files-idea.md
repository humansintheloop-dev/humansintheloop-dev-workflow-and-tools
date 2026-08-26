# Handle Failed Commit for Idea Files

## Problem

When the user selects **Commit changes** from the `i2code go` menu in the
`HAS_PLAN` state, `Orchestrator._commit_changes`
(`src/i2code/go_cmd/orchestrator.py:359`) runs `git add` and `git commit`
without checking return codes or capturing output. Pre-commit hooks
(`ruff`, `pyright`, `shellcheck`, `gitleaks`, …) can fail the commit
silently from the orchestrator's perspective.

Example: `gitleaks` flagging local-unix-home-path "secrets" in idea/spec/
discussion markdown files:

```
Detect hardcoded secrets.................................................Failed
- hook id: gitleaks
- exit code: 1

Finding:     the container at `REDACTEDrepo`
RuleID:      local-unix-home-path
File:        docs/ideas/active/checking-completed-tasks/checking-completed-tasks-discussion.md
Line:        108
...
6:28PM WRN leaks found: 3
```

The user is dropped back to the menu in a confusing state (commit didn't
happen but i2code didn't react to it).

## Refined Idea

When the `Commit changes` menu action fails because `git commit` returns
non-zero, `i2code` should:

1. **Stream and capture** the `git commit` output (tee): the user keeps the
   live view of hook output, and i2code retains the full text for the prompt.
2. On non-zero exit, **prompt the user (Y/n)** asking whether to launch
   Claude interactively to fix the problem.
3. If **yes** → launch Claude interactively (via `ClaudeRunner`, same pattern
   as brainstorm/spec/plan) using a new Jinja template that includes:
   - the captured hook output (full),
   - the staged file scope (idea directory / file paths),
   - instructions for Claude to **fix the files AND perform the commit
     itself** (i2code does not re-run the commit).
   Claude runs in the **git repo root**.
4. If **no** → return to the main menu silently (output was already shown).
5. After the Claude session ends → return to the main menu unconditionally.
   No verification, no warning. The next menu iteration will reflect the
   actual repo state (via the existing `_has_uncommitted_changes` check).

`git add` failures (which run before hooks) keep the current simple
behavior: print the error and return to the menu. Only `git commit`
failures trigger the new Claude flow.

## Scope

- **In scope:** `Orchestrator._commit_changes`
  (`src/i2code/go_cmd/orchestrator.py:359-367`) and the menu path that
  invokes it.
- **Out of scope:** Other i2code commit paths (`execute_transition` in
  `idea_cmd/state_cmd.py`, archive commands) — they keep current behavior.
  Generalizing the recovery mechanism is a follow-up idea, not part of
  this one.

## Classification

User-facing feature — modifies an observable step of the interactive
`i2code go` workflow. See discussion file for rationale.
