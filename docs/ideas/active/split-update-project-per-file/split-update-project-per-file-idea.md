# Split update-project into per-file Claude invocations

## Problem

`i2code setup update-project` currently renders one prompt that targets both
`CLAUDE.md` and `.claude/settings.local.json`, and invokes Claude a single time
to update both files (src/i2code/setup_cmd/update_project.py:48-60). This has
three drawbacks:

1. **No-op Claude runs when there's nothing to do.** Claude is invoked even
   when only one of the two files has changed in the template — or when the
   target file doesn't exist in the project and just needs to be copied.
2. **One prompt for two unrelated files.** Bundling `CLAUDE.md` and
   `settings.local.json` into a single prompt makes the model triage both file
   types in one session, increasing the chance of cross-contamination and
   making the prompt harder to specialize (markdown reconciliation vs JSON
   permissions merging).
3. **Single shared SHA in CLAUDE.md couples bookkeeping to a content file.**
   The previous SHA is stored in a comment inside the project's `CLAUDE.md`
   (src/i2code/setup_cmd/update_project.py:63-73). A single shared SHA also
   means both files appear "changed" even when only one was touched in the
   template repo.

## Goal

Restructure `update-project` so that:

1. **Each target file is tracked by its own SHA**, stored inside that file:
   - `CLAUDE.md` keeps the existing `<!-- claude-config-files-sha: ... -->`
     HTML comment marker.
   - `settings.local.json` gets a fake permission entry,
     `Bash(i2code-config-files-sha <sha>)`, in the `permissions.allow` array.
2. **Missing target files are copied directly** from the config-files
   directory into the project, with no Claude invocation. After copy, Python
   writes the per-file SHA marker into the copied file.
3. **Claude is invoked at most once per existing target file**, and only when
   that file's slice of the git diff
   (`git diff <prev>..<curr> -- <file>`) is non-empty.
4. **Python writes the SHA markers after Claude succeeds**, deterministically.
   The per-file prompts never mention the SHA marker — Claude focuses purely
   on content reconciliation.
5. **CLAUDE.md is processed first, then settings.local.json.** If Claude
   exits non-zero on the first file, abort: skip the second file and update
   no SHAs. The user re-runs after addressing the failure.

## Per-file flow

For each of `CLAUDE.md` and `settings.local.json`:

1. **File missing in project** → copy from template; write current per-file
   SHA marker into the copied file. No Claude invocation.
2. **File present, no SHA marker** → first-sync for that file. Render the
   file-specific prompt with the full current template as reference; invoke
   Claude; on success, Python writes the SHA marker.
3. **File present, SHA marker found, per-file diff empty** → no Claude
   invocation; Python just advances the SHA marker to the current per-file
   SHA.
4. **File present, SHA marker found, per-file diff non-empty** → render the
   file-specific prompt scoped to that file's diff; invoke Claude; on success,
   Python writes the new SHA marker.

## Locations

**Definition**
- src/i2code/setup_cmd/update_project.py:9 — `update_project` orchestrates the
  whole flow; this is the function to split into per-file steps.
- src/i2code/setup_cmd/update_project.py:63 — `_extract_previous_sha` is
  CLAUDE.md-specific today; an equivalent reader is needed for the
  settings.local.json fake permission entry.

**Construction sites**
- src/i2code/setup_cmd/cli.py:25 — `update-project` Click command; the public
  interface does not change (`i2code setup update-project [PROJECT_DIR]
  [--config-dir ...]`).

**Call sites / prompts**
- src/i2code/prompt-templates/update-project-claude-files.md — current single
  prompt is split into two specialized templates (e.g.
  `update-project-claude-md.md` and `update-project-settings.md`). The
  SHA-write instruction (current lines 35-38) is removed entirely — Python
  owns SHA writes now.

**Unchanged**
- src/i2code/setup_cmd/claude_files.py — initial `claude-files` setup is out of
  scope.
- Git machinery (`_get_repo_root`, `_get_current_sha`, `_get_config_diff`) —
  retained, but invoked per file rather than for the directory as a whole
  (per-file paths in the `git log -1` and `git diff` arguments).

## Out of scope

- Generalizing the orchestrator to "all files in config_dir." Scope is the
  two known target files; each has its own marker scheme.
- Changes to `i2code setup claude-files`.
- Changes to the public CLI surface.
