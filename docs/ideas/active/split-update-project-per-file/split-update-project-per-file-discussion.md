# Discussion: Split update-project into per-file Claude invocations

## Codebase context (gathered before questioning)

- `update_project` orchestrator lives at src/i2code/setup_cmd/update_project.py:9. It validates dirs, extracts the previous SHA from the project's `CLAUDE.md` (src/i2code/setup_cmd/update_project.py:63), derives the git repo root from `config_dir`, computes current SHA + git diff, renders one template, and invokes `claude_runner.run_interactive` once.
- The single prompt lives at src/i2code/prompt-templates/update-project-claude-files.md and bundles both target files. It instructs Claude to write `<!-- claude-config-files-sha: $CURRENT_SHA -->` into `CLAUDE.md` (lines 35-38).
- The Click entry point is src/i2code/setup_cmd/cli.py:25 — public CLI interface is `i2code setup update-project [PROJECT_DIR] [--config-dir ...]`.
- Initial copy (`i2code setup claude-files`) lives at src/i2code/setup_cmd/claude_files.py — out of scope per the idea.
- The synced config-files set contains exactly two files today: `CLAUDE.md` and `settings.local.json` (src/i2code/config_files/).
- Existing test coverage: tests/setup-cmd/test_update_project.py exercises directory validation, SHA extraction, git operations, template rendering, and Claude invocation through `fake_runner` / `fake_renderer` fixtures.

## Q&A

### Q1: Who writes the SHA-tracking entry in `.claude/settings.local.json`?

Options presented: (A) Python after Claude, (B) Claude via prompt, (C) Python before Claude.

Context: today Claude writes the SHA via prompt instruction in src/i2code/prompt-templates/update-project-claude-files.md:35-38.

**Answer: Python writes, after Claude.** The orchestrator deterministically writes/updates the fake permission entry in `settings.local.json` after the per-file Claude invocations complete. The per-file prompts say nothing about the SHA marker — Claude focuses purely on reconciling content changes.

### Q2: When a target file exists in the project AND its per-file diff is empty, invoke Claude or skip?

**Answer: Skip Claude for that file.** Per-file diff slicing means we already know the template hasn't changed for that file since last sync — there is nothing to reconcile. Python still writes the new SHA so the marker advances to `current_sha`.

### Q3: Migration of the legacy SHA marker in CLAUDE.md

The original question assumed a single shared SHA being moved from CLAUDE.md to settings.local.json. **Correction from user:** SHAs are tracked **per file**, with each marker stored inside the file it tracks:

- `CLAUDE.md` keeps the existing `<!-- claude-config-files-sha: ... -->` HTML comment (legacy mechanism retained).
- `settings.local.json` gets its own SHA stored as a fake permission entry, e.g. `Bash(fakecommand <sha>)`.

Implications:
- Previous/current SHAs and diffs are computed per file (`git log -1 -- <file>`, `git diff prev..curr -- <file>`).
- No migration step needed for CLAUDE.md.
- The original idea's drawback #3 (\"breaks if no CLAUDE.md yet\") is resolved because tracking is independent per file — missing CLAUDE.md no longer prevents tracking settings.local.json.

### Q4: File exists but has no SHA marker (first sync for that file)

**Answer: Invoke Claude with a first-sync prompt.** Preserves today's behavior: per-file prompt says \"no previous SHA, here's the full current template as reference\" and Claude reconciles the existing file against the full template. Safer than silent adoption when files may have drifted.

### Q5: Claude failure handling across the two files

**Answer: Abort on first failure.** If the first file's Claude session exits non-zero, skip the second file and update no SHAs. Simplest mental model; user fixes the issue and re-runs. Trade-off accepted: second file's potential work is deferred until the first succeeds.

### Q6: Per-file prompt template structure

**Answer: Two specialized templates** (e.g. `update-project-claude-md.md` and `update-project-settings.md`). Each template can give file-type-specific reconciliation guidance — markdown section merging for CLAUDE.md, permissions-array merging for settings.local.json — without genericity getting in the way.

### Q7: Who writes the CLAUDE.md SHA marker in the new design?

**Answer: Python writes, after Claude.** Consistent rule with settings.local.json (Q1): the orchestrator updates the HTML comment after Claude's edits succeed. Neither per-file prompt mentions the marker — Claude focuses purely on content reconciliation.

### Q8: Fake permission entry format in settings.local.json

**Answer:** `Bash(i2code-config-files-sha <sha>)`. Self-documenting: the fake command name signals what the entry represents and is easy to grep/regex. Lives in the `permissions.allow` array.

### Q9: Order of file processing

**Answer: CLAUDE.md first, then settings.local.json.** Process the larger, more substantive content file first; permissions reconciliation second. With abort-on-first-failure semantics (Q5), if CLAUDE.md fails, settings.local.json is deferred until next run.

## Classification

**Type: C. Platform/infrastructure capability.**

Rationale: This is a refactor of an internal command of the `i2code` CLI — the platform that supports the genai-development-workflow project. It is not a product feature for end users (A), not a proof-of-concept for an architectural concern (B), and not a teaching artifact (D). It improves a tooling capability (`i2code setup update-project`) that maintainers of i2code-managed projects rely on, restructuring its internal execution model (per-file rather than bundled) and its bookkeeping model (per-file SHAs rather than one shared SHA). The CLI surface is unchanged; only internal flow and on-disk state representation change.

## Downstream impact survey

- **Tests** — tests/setup-cmd/test_update_project.py will need substantial rewrites: per-file orchestration, two prompt templates, new SHA reader/writer for settings.local.json, new flow branches (missing file, no marker, empty diff, non-empty diff).
- **Prompt templates** — src/i2code/prompt-templates/update-project-claude-files.md will be replaced by two new templates; SHA-write instruction removed from prompts entirely.
- **On-disk state in users' projects** — `.claude/settings.local.json` will contain a new fake permission entry `Bash(i2code-config-files-sha <sha>)` after the first run with the new code. Users who hand-inspect their settings file will see this; worth documenting.
- **No event/messaging consumers** — this is a CLI tool, not a service; no event-flow downstream effects.
- **No CQRS replicas or shared infrastructure**.
- **CLI surface unchanged** — no breaking change for callers/scripts that invoke `i2code setup update-project`.

