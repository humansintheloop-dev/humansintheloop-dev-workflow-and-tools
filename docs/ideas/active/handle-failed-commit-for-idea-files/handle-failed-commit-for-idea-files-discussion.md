# Discussion: Handle Failed Commit for Idea Files

## Context (from idea file)

When the user selects "Commit changes" from the `i2code go` menu (HAS_PLAN state)
for an idea, the commit can fail because of pre-commit hooks. In the example,
the `gitleaks` hook detected a local-unix-home-path "secret" in
`docs/ideas/active/checking-completed-tasks/checking-completed-tasks-discussion.md`
and `checking-completed-tasks-spec.md`.

The idea: when the commit fails, `i2code` should offer to run Claude
interactively to fix the problem.

## Codebase Analysis (pre-discussion)

- Commit logic for idea-file changes lives in
  `src/i2code/go_cmd/orchestrator.py:359-367` (`Orchestrator._commit_changes`).
  It currently calls `git add <dir>` and `git commit -m ... -- <dir>` through
  `git_runner` **without capturing output or checking return codes**, so a
  pre-commit hook failure is silent to the orchestrator.
- A similar Claude-driven commit recovery already exists for the implement
  loop: `src/i2code/implement/commit_recovery.py` plus the Jinja template
  `src/i2code/implement/templates/commit_recovery.j2`, invoked through
  `CommandBuilder.build_recovery_command(...)`. That recovery is
  **non-interactive** and is aimed at "completed task, missing commit"
  recovery, not at fixing the underlying hook violations.
- Pre-commit hooks visible in the failure log: `ruff check --fix`, `pyright`,
  `shellcheck`, and `gitleaks`. Any of them can cause a non-zero exit from
  `git commit`.

## Questions and Answers

### Q1: When the commit fails due to a pre-commit hook, how should i2code respond?

**Options:**
- A. Prompt before launching Claude — show the failure output and ask the user (Y/n) before launching Claude interactively.
- B. Launch Claude automatically — immediately launch an interactive Claude session.
- C. Offer a menu — present (1) Launch Claude to fix, (2) Retry commit, (3) Abort.

**Answer:** A — Prompt before launching Claude. Show the failure output and ask the user to confirm (Y/n) before launching the interactive Claude session.

### Q2: What context should i2code give to the interactive Claude session?

**Options:**
- A. Full hook output + file scope — pass captured commit stderr/stdout AND the list/paths of staged files (idea directory).
- B. Just hook output — pass only the captured commit output; Claude infers files from the error messages.
- C. Free-form, no preset context — launch bare `claude` in the working dir; user types the request.

**Answer:** A — Pass both the full captured hook output and the file scope (the idea directory / staged paths) in the Claude prompt.

### Q3: What should Claude be instructed to do in this interactive session?

**Options:**
- A. Fix files, then commit — Claude edits the offending files AND runs `git add` / `git commit` itself once the hooks pass.
- B. Fix files only; i2code re-commits — Claude only fixes the files; control returns to i2code which re-runs `git add` / `git commit`.
- C. Open-ended — prompt explains the situation but the user drives.

**Answer:** A — Claude is responsible for both fixing the offending files and performing the commit. i2code does not re-run the commit afterward.

### Q4: After the interactive Claude session ends, what should i2code do?

**Options:**
- A. Verify commit happened, return to menu — check `HEAD`/`git status` to confirm a new commit exists; warn if not.
- B. Always return to menu, no check — return to the main menu and let the user inspect state.
- C. Exit i2code go — exit so the user can review and resume manually.

**Answer:** B — Always return to the main `i2code go` menu after the Claude session ends. Do not re-verify or warn. The menu (with `_has_uncommitted_changes`) will already reflect the new state on its next iteration.

### Q5: If the user declines the Y/n prompt (chooses not to launch Claude), what should happen?

**Options:**
- A. Return to menu silently — the failure output was already shown; return to the main menu.
- B. Print a hint, return to menu — print "You can fix the issues manually and re-select Commit changes." and return.
- C. Exit i2code go — exit so the user can address the issue in their own shell.

**Answer:** A — Return to the menu silently. The captured hook output is sufficient; no extra hint needed.

### Q6: Scope — which i2code commit paths get this failure handling?

**Options:**
- A. Only orchestrator `_commit_changes` (the `Commit changes` menu option in `i2code go`).
- B. All idea-related i2code commits — orchestrator, `execute_transition`, archive.
- C. Orchestrator now, others later.

**Answer:** A — Only the orchestrator's `_commit_changes` (the `Commit changes` menu option). Other commit paths (`execute_transition`, archive) keep their current behavior.

### Q7: How to handle commit output (current behavior streams directly to terminal)?

**Options:**
- A. Capture, then echo on failure — `capture_output=True`; on failure print captured stdout+stderr.
- B. Stream and capture (tee) — show hook output live as it runs AND capture it for the Claude prompt.
- C. Capture silently, summarize — capture all output; on failure print a short summary.

**Answer:** B — Stream output live (so the user keeps the current UX of watching hooks run) **and** capture it so we can pass it to Claude on failure.

### Q8: How should `git add` failures be handled?

**Options:**
- A. Same flow as commit failure — capture, prompt Y/n, optionally launch Claude.
- B. `git add` failures: print and return — only `git commit` failures trigger the Claude flow.
- C. Ignore `git add` failures — keep current no-check behavior.

**Answer:** B — `git add` failures print the error and return to the menu. Only `git commit` failures (where pre-commit hooks live) trigger the new Claude flow.

### Q9: How should the interactive Claude be invoked?

**Options:**
- A. New i2code template + `ClaudeRunner` interactive — add a Jinja template (e.g. `commit_hook_recovery.j2`), render it with the failure output + paths, and launch Claude interactively (same pattern as brainstorm/spec/plan).
- B. Reuse `CommandBuilder.build_recovery_command(interactive=True)` — pass the hook output as the diff summary; no new template, but prompt doesn't mention hook failures.
- C. Inline prompt string — construct prompt directly in `_commit_changes`.

**Answer:** A — Add a new Jinja template dedicated to this case and launch via the existing `ClaudeRunner` interactive path, mirroring the other i2code steps.

### Q10: What working directory should the interactive Claude run in?

**Options:**
- A. Git repo root — matches how brainstorm/spec/plan launch Claude.
- B. Idea directory — narrower scope but requires relative paths for git commands.

**Answer:** A — Run Claude in the git repository root, same as the other interactive Claude steps in i2code.

### Q11: Classification

**Options:**
- A. User-facing feature
- B. Platform/infrastructure capability
- C. Architecture POC
- D. Educational/example

**Answer:** A — User-facing feature.

## Classification & Rationale

**Classification:** A — User-facing feature.

**Rationale:**
- Changes a directly visible step in the `i2code go` interactive workflow: the
  `Commit changes` menu option in `WorkflowState.HAS_PLAN`.
- The new behavior (capture+tee output, prompt Y/n, launch interactive Claude
  with a rendered template) is observable end-to-end by the user.
- Scope is intentionally narrow (Q6 → only `Orchestrator._commit_changes`),
  not a generic platform capability.
- All underlying mechanisms (interactive Claude via `ClaudeRunner`, Jinja
  prompt templates, captured-output recovery) are already proven elsewhere in
  i2code (`commit_recovery.py`, brainstorm/spec/plan steps), so this is not
  an architecture POC.

### Q12: Any additional requirements or concerns before moving to the spec step?

**Answer:** No — proceed to the specification step.

