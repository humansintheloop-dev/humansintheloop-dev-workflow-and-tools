# Platform Capability Specification: Per-file `update-project` flow

## Purpose and context

The `i2code setup update-project` command pushes updates from the
`config-files` template directory into a downstream project's Claude
configuration files (`CLAUDE.md` and `.claude/settings.local.json`). Today the
implementation (src/i2code/setup_cmd/update_project.py:9) renders a single
prompt and invokes Claude once for both files, and stores a single shared
template SHA as an HTML comment inside the project's `CLAUDE.md`.

This specification restructures the command so that:

1. Each target file is tracked by its own template SHA, stored inside that
   file.
2. Missing target files are copied without invoking Claude.
3. Claude is invoked at most once per existing file, only when the per-file
   diff is non-empty, with a file-type-specific prompt.
4. Python (not Claude) writes the SHA markers deterministically after the
   Claude session completes.

The public CLI surface (`i2code setup update-project [PROJECT_DIR]
[--config-dir ...]`, src/i2code/setup_cmd/cli.py:25) does not change.

## Consumers

- **`i2code` CLI users** — developers running `i2code setup update-project`
  against a project that has previously been set up via
  `i2code setup claude-files`.
- **`update_project` Click command** (src/i2code/setup_cmd/cli.py:25) — the
  in-process consumer that calls the orchestrator function.
- **Test suite** (tests/setup-cmd/test_update_project.py) — exercises the
  orchestrator via `fake_runner` and `fake_renderer` fixtures.

No external services, event consumers, CQRS replicas, or other downstream
systems consume this capability. State changes are local to the target
project directory.

## Target files (fixed scope)

The capability operates on exactly two files in the target project:

| Target file in project | Source file in `config_dir` | SHA marker location and format |
|---|---|---|
| `<project_dir>/CLAUDE.md` | `<config_dir>/CLAUDE.md` | HTML comment at end of file: `<!-- claude-config-files-sha: <sha> -->` |
| `<project_dir>/.claude/settings.local.json` | `<config_dir>/settings.local.json` | Fake permission entry in `permissions.allow`: `Bash(i2code-config-files-sha <sha>)` |

Generalization to "all files in `config_dir`" is out of scope.

## Capabilities and behaviors

### CAP-1: Per-file SHA tracking

Each target file carries its own previous-SHA marker. The orchestrator must:

- **CAP-1.1** Read a per-file previous SHA from each target file using the
  file-specific marker format defined in the table above.
- **CAP-1.2** Resolve a per-file current SHA via
  `git log -1 --format=%H -- <relative_path_to_template_file>` executed from
  the template repo root.
- **CAP-1.3** Compute a per-file diff via
  `git diff <prev_sha>..<curr_sha> -- <relative_path_to_template_file>`
  executed from the template repo root.
- **CAP-1.4** Write the new per-file SHA marker into the target file after
  the file's flow completes successfully (see CAP-3, CAP-4).

A missing marker (file exists, no marker found) yields an empty previous SHA
and is treated as first-sync for that file.

### CAP-2: Direct copy of missing files (no Claude)

For each target file:

- **CAP-2.1** If the target file does not exist in the project, copy the
  corresponding source file from `config_dir` into the project. For
  `CLAUDE.md`, the destination is `<project_dir>/CLAUDE.md`. For
  `settings.local.json`, the destination is
  `<project_dir>/.claude/settings.local.json`, creating `.claude/` if absent.
- **CAP-2.2** After copying, Python writes the per-file SHA marker into the
  copied file (CAP-1.4) using the current per-file SHA.
- **CAP-2.3** No Claude invocation occurs for missing-file copies.

### CAP-3: Per-file Claude invocation, scoped to per-file diff

For each target file present in the project:

- **CAP-3.1** If the per-file diff is empty AND the previous SHA is present,
  skip Claude. Python writes the new per-file SHA marker (CAP-1.4) so the
  marker advances to `current_sha`.
- **CAP-3.2** If the previous SHA is absent (file present, no marker),
  render the file-specific prompt as a first-sync prompt that includes the
  full current template file's content as reference instead of a diff, and
  invoke Claude.
- **CAP-3.3** If the previous SHA is present and the per-file diff is
  non-empty, render the file-specific prompt scoped to that file's diff and
  invoke Claude.
- **CAP-3.4** Claude is invoked via `ClaudeRunner.run_interactive`, with
  `cwd=project_dir`, matching today's invocation pattern
  (src/i2code/setup_cmd/update_project.py:59-60).
- **CAP-3.5** Per-file prompts never reference the SHA marker or instruct
  Claude to write it.

### CAP-4: Python writes SHA markers after Claude succeeds

- **CAP-4.1** For each target file processed (whether copied, skipped due to
  empty diff, or reconciled by Claude), Python writes the new per-file SHA
  marker only if all prior steps for that file completed successfully.
- **CAP-4.2** For `CLAUDE.md`, the marker is written as the last line of the
  file in the format `<!-- claude-config-files-sha: <sha> -->`. If a marker
  already exists, it is replaced in place; otherwise a new marker line is
  appended.
- **CAP-4.3** For `settings.local.json`, the marker is written as an entry in
  the `permissions.allow` array in the format
  `Bash(i2code-config-files-sha <sha>)`. If an existing
  `Bash(i2code-config-files-sha ...)` entry is present, it is replaced;
  otherwise the entry is appended to the `allow` array. JSON structure
  (formatting, key order) is preserved as far as practical.

### CAP-5: Fixed processing order and abort-on-first-failure

- **CAP-5.1** Files are processed in this order: (1) `CLAUDE.md`,
  (2) `settings.local.json`.
- **CAP-5.2** If Claude exits non-zero for the first file, the orchestrator
  aborts: it does not process the second file, and it does not write any
  SHA marker for either file.
- **CAP-5.3** If the first file is handled without invoking Claude (missing
  file copy, or empty-diff skip), the second file is processed normally.
- **CAP-5.4** The Click command returns a `ClaudeResult` reflecting the
  outcome (per CAP-7).

### CAP-6: Directory validation

Preserved from the existing implementation:

- **CAP-6.1** If `project_dir` does not exist, print an error to stderr and
  raise `SystemExit(1)` before any work begins.
- **CAP-6.2** If `config_dir` does not exist, print an error to stderr and
  raise `SystemExit(1)` before any work begins.
- **CAP-6.3** Validation messages match today's format: `Error: Project
  directory not found: <path>` and `Error: Config directory not found:
  <path>`.

### CAP-7: Result reporting

- **CAP-7.1** The orchestrator function returns a `ClaudeResult` whose
  `returncode` is `0` when the overall run is successful. Successful here
  means: every file processed reached a clean terminal state (copied,
  skipped, or Claude exit code 0).
- **CAP-7.2** If a Claude invocation exits non-zero, the function returns
  the failing `ClaudeResult` from that invocation (matching CAP-5.2 abort
  semantics).
- **CAP-7.3** If no Claude invocation was performed (both files were missing
  or empty-diff), the function returns a `ClaudeResult(returncode=0)`.

## High-level APIs, contracts, integration points

### Public CLI surface (unchanged)

```
i2code setup update-project [PROJECT_DIR] [--config-dir <dir>]
```

- `PROJECT_DIR` defaults to `.`
- `--config-dir` defaults to `default_config_dir()` from
  `i2code.config_files`.

### Orchestrator function signature (preserved)

```python
def update_project(project_dir, config_dir, claude_runner, template_renderer):
    """Returns ClaudeResult."""
```

Located at src/i2code/setup_cmd/update_project.py:9. The function's
parameters and return type do not change. The internal flow is replaced.

### Prompt templates (new)

Two new templates replace
src/i2code/prompt-templates/update-project-claude-files.md:

1. **`src/i2code/prompt-templates/update-project-claude-md.md`** — prompt for
   reconciling `CLAUDE.md`. Receives the variables:
   - `PROJECT_DIR`
   - `PROJECT_CLAUDE_MD` (absolute path)
   - `CONFIG_CLAUDE_MD` (absolute path)
   - `CURRENT_SHA` (per-file)
   - `PREVIOUS_SHA` (per-file; empty string on first sync)
   - `CONFIG_DIFF` (per-file diff string; on first sync, the full current
     template content with a leading explanatory message)
   - `IS_FIRST_SYNC` (`"true"` or `"false"`)

   The prompt instructs Claude on markdown-specific reconciliation:
   preserving project-specific sections, merging new template sections,
   asking the user before applying each change. The prompt must NOT
   reference the SHA marker.

2. **`src/i2code/prompt-templates/update-project-settings.md`** — prompt for
   reconciling `settings.local.json`. Receives the same set of variables
   adapted for settings:
   - `PROJECT_DIR`
   - `PROJECT_SETTINGS` (absolute path to
     `<project_dir>/.claude/settings.local.json`)
   - `CONFIG_SETTINGS` (absolute path)
   - `CURRENT_SHA` (per-file)
   - `PREVIOUS_SHA` (per-file; empty string on first sync)
   - `CONFIG_DIFF` (per-file diff string; on first sync, the full current
     template content with a leading explanatory message)
   - `IS_FIRST_SYNC` (`"true"` or `"false"`)

   The prompt instructs Claude on JSON-permissions-specific reconciliation:
   merging new entries into `permissions.allow`/`deny`/`ask` arrays,
   preserving project-specific entries, asking before applying each change.
   The prompt must NOT reference the SHA marker.

The existing `update-project-claude-files.md` template is deleted.

### Internal helpers (new and revised)

- `_read_claude_md_sha(claude_md_path) -> str` — reads the
  `<!-- claude-config-files-sha: ... -->` marker; returns `""` if absent.
  Replaces the existing `_extract_previous_sha`
  (src/i2code/setup_cmd/update_project.py:63).
- `_write_claude_md_sha(claude_md_path, sha) -> None` — writes/replaces the
  HTML comment marker as the last line.
- `_read_settings_sha(settings_path) -> str` — reads the
  `Bash(i2code-config-files-sha ...)` entry from `permissions.allow`;
  returns `""` if absent.
- `_write_settings_sha(settings_path, sha) -> None` — writes/replaces the
  fake permission entry in `permissions.allow`.
- `_get_per_file_current_sha(repo_root, template_file_relpath) -> str` —
  replaces today's directory-scoped `_get_current_sha` (which globs
  `<config_rel_path>/`).
- `_get_per_file_diff(repo_root, template_file_relpath, prev_sha, curr_sha) -> str`
  — replaces today's directory-scoped `_get_config_diff`.
- `_copy_template_file(source_path, dest_path) -> None` — copies a file,
  creating parent directories as needed (for `.claude/`).

Existing `_get_repo_root` is retained unchanged.

### Integration with `ClaudeRunner` and `template_renderer`

Both interfaces are unchanged. `claude_runner.run_interactive(cmd, cwd=...)`
is called per file; `template_renderer(template_name, variables)` is called
per file with the variables enumerated above.

## Non-functional requirements

- **NFR-1: Determinism.** SHA reads, SHA writes, file ordering, and abort
  semantics must be deterministic across runs given the same on-disk inputs.
- **NFR-2: Idempotence.** Running the command twice in a row with no
  template changes between runs must produce no Claude invocations on the
  second run (both files have empty per-file diffs).
- **NFR-3: No silent data loss.** SHA-marker writes must preserve file
  content otherwise. For `CLAUDE.md`, only the marker line is added or
  replaced. For `settings.local.json`, only the
  `Bash(i2code-config-files-sha ...)` entry in `permissions.allow` is
  added/replaced; other keys, ordering, and entries are preserved.
- **NFR-4: Test parity.** The new implementation must be testable through
  the existing `fake_runner` / `fake_renderer` test fixtures
  (tests/setup-cmd/conftest.py — implied by test file usage). Tests must
  cover all branches of the per-file flow (missing, first-sync, empty-diff,
  non-empty-diff) for both files and the abort-on-failure semantic.
- **NFR-5: CLI compatibility.** The public CLI surface, exit codes, and
  validation error messages match today's behavior (CAP-6).
- **NFR-6: No performance SLA.** This is a developer tool run on demand;
  latency is dominated by Claude session duration. No latency budget is
  imposed beyond "don't spin up Claude when not needed" (CAP-2.3, CAP-3.1).

## Scenarios and workflows

### Scenario S-1 (primary end-to-end): Routine update with both files present and both diffs non-empty

**Pre-conditions:**
- `project_dir` exists and is a valid project directory.
- `config_dir` is a clean git working tree.
- Project's `CLAUDE.md` exists and contains
  `<!-- claude-config-files-sha: AAA111 -->`.
- Project's `.claude/settings.local.json` exists and contains
  `Bash(i2code-config-files-sha BBB222)` in `permissions.allow`.
- Template's `CLAUDE.md` was last touched at commit `CCC333`; the diff
  `AAA111..CCC333 -- src/i2code/config_files/CLAUDE.md` is non-empty.
- Template's `settings.local.json` was last touched at commit `DDD444`; the
  diff `BBB222..DDD444 -- src/i2code/config_files/settings.local.json` is
  non-empty.

**Flow:**

1. Click command resolves `config_dir`, constructs `ClaudeRunner`, and calls
   `update_project`.
2. `update_project` validates `project_dir` and `config_dir` exist.
3. `update_project` resolves `repo_root` via `git rev-parse --show-toplevel`
   from `config_dir`.
4. **Process CLAUDE.md:**
   a. Read previous SHA from project's CLAUDE.md → `AAA111`.
   b. Resolve current per-file SHA for template CLAUDE.md → `CCC333`.
   c. Compute per-file diff `AAA111..CCC333 -- <config>/CLAUDE.md` → non-empty.
   d. Render `update-project-claude-md.md` with `IS_FIRST_SYNC=false`,
      `PREVIOUS_SHA=AAA111`, `CURRENT_SHA=CCC333`, `CONFIG_DIFF=<diff>`, and
      both file paths.
   e. Invoke `claude_runner.run_interactive(["claude", prompt],
      cwd=project_dir)`. Claude exits 0.
   f. Python writes/replaces `<!-- claude-config-files-sha: CCC333 -->` as
      the last line of project's CLAUDE.md.
5. **Process settings.local.json:**
   a. Read previous SHA from project's settings.local.json → `BBB222`.
   b. Resolve current per-file SHA → `DDD444`.
   c. Compute per-file diff → non-empty.
   d. Render `update-project-settings.md`.
   e. Invoke Claude. Claude exits 0.
   f. Python writes/replaces the `Bash(i2code-config-files-sha DDD444)`
      entry in `permissions.allow`.
6. Return `ClaudeResult(returncode=0)`.

**Post-conditions:**
- Project's CLAUDE.md marker is `CCC333`.
- Project's settings.local.json marker is `DDD444`.
- File content beyond the markers reflects Claude's reconciliation edits.

### Scenario S-2: Only CLAUDE.md changed in template

**Pre-conditions:** Same as S-1 but the per-file diff for settings.local.json
is empty (`prev == curr` for that file).

**Flow:** S-1 steps 1-4 proceed identically (Claude is invoked for
CLAUDE.md). Step 5 short-circuits: per-file diff for settings.local.json is
empty, so no Claude invocation; Python writes the new settings.local.json
marker only.

### Scenario S-3: First sync for an existing file

**Pre-conditions:** Project's CLAUDE.md exists but contains no
`<!-- claude-config-files-sha: ... -->` marker. settings.local.json is fully
synced (SHA marker present, empty per-file diff).

**Flow:**

1. Validation passes.
2. **Process CLAUDE.md:**
   a. Previous SHA read → `""`.
   b. Current per-file SHA → e.g. `CCC333`.
   c. Render `update-project-claude-md.md` with `IS_FIRST_SYNC=true`,
      `PREVIOUS_SHA=""`, `CONFIG_DIFF=<message with full current template
      content as reference>`.
   d. Invoke Claude. On success, Python writes the marker.
3. **Process settings.local.json:** empty per-file diff → no Claude;
   marker advances.
4. Return `ClaudeResult(returncode=0)`.

### Scenario S-4: Missing file is copied

**Pre-conditions:** Project's CLAUDE.md is absent. settings.local.json
exists, with valid SHA marker, empty per-file diff.

**Flow:**

1. Validation passes.
2. **Process CLAUDE.md:**
   a. Detect the file is missing.
   b. Copy `<config_dir>/CLAUDE.md` to `<project_dir>/CLAUDE.md`.
   c. Resolve current per-file SHA.
   d. Append `<!-- claude-config-files-sha: <sha> -->` as the last line of
      the copied file.
   e. No Claude invocation.
3. **Process settings.local.json:** empty per-file diff → no Claude;
   marker advances.
4. Return `ClaudeResult(returncode=0)`.

### Scenario S-5: Claude fails on CLAUDE.md

**Pre-conditions:** Both files present, both per-file diffs non-empty.

**Flow:**

1. CLAUDE.md flow reaches the Claude invocation; Claude exits non-zero.
2. Orchestrator does NOT write a SHA marker for CLAUDE.md.
3. Orchestrator does NOT process settings.local.json.
4. Return the failing `ClaudeResult`.

**Post-conditions:**
- Project's CLAUDE.md SHA marker is unchanged from before the run.
- Project's settings.local.json SHA marker is unchanged from before the run.
- Any edits Claude made before exiting non-zero remain on disk (this matches
  the existing tool's behavior — the orchestrator does not roll back partial
  edits).

### Scenario S-6: Both files missing (clean project)

**Pre-conditions:** Project has no `CLAUDE.md` and no
`.claude/settings.local.json`.

**Flow:**

1. Validation passes (project_dir and config_dir exist).
2. CLAUDE.md is copied and its marker written.
3. settings.local.json is copied (creating `.claude/`) and its marker
   written.
4. No Claude invocations occur.
5. Return `ClaudeResult(returncode=0)`.

## Constraints and assumptions

- **C-1** Target files are exactly the two listed in the "Target files"
  table. Adding/removing target files is out of scope.
- **C-2** The `config_dir` is inside a git repository; `git rev-parse
  --show-toplevel`, `git log`, and `git diff` operate over the template
  repo. (Today's behavior is preserved; if `git rev-parse` fails, current
  SHA and diff are empty — and per CAP-3.2, the empty previous SHA triggers
  first-sync prompts for files that exist.)
- **C-3** The `settings.local.json` template file has a
  `permissions.allow` array. (Verified at
  src/i2code/config_files/settings.local.json:3-68.)
- **C-4** `template_renderer` is the existing `i2code.template_renderer`
  module's `render_template` callable.
- **C-5** `ClaudeRunner.run_interactive` semantics are unchanged.
- **C-6** Existing initial-copy command `i2code setup claude-files`
  (src/i2code/setup_cmd/claude_files.py) is not modified; if its template
  files start carrying SHA markers, that is handled by a separate idea/spec.

## Acceptance criteria

The new capability is accepted when all of the following hold:

- **AC-1** Running `i2code setup update-project` in scenario S-1 invokes
  Claude twice (once per file), in CLAUDE.md-then-settings order, with
  per-file prompts rendered from `update-project-claude-md.md` and
  `update-project-settings.md` respectively. After the run, each project
  file's SHA marker equals the per-file current SHA.
- **AC-2** Running in scenario S-2 invokes Claude exactly once (for
  CLAUDE.md). After the run, both files' SHA markers are updated.
- **AC-3** Running in scenario S-3 invokes Claude with `IS_FIRST_SYNC=true`
  for CLAUDE.md and passes the full current template content (with an
  explanatory leading message) as `CONFIG_DIFF`. After the run, the
  CLAUDE.md marker exists and equals the current per-file SHA.
- **AC-4** Running in scenario S-4 copies the missing CLAUDE.md from the
  template, writes its SHA marker, and does NOT invoke Claude for that
  file.
- **AC-5** Running in scenario S-5 leaves both SHA markers unchanged and
  returns a `ClaudeResult` with a non-zero `returncode` matching the failed
  Claude session.
- **AC-6** Running in scenario S-6 produces both files in the project
  (creating `.claude/` if needed), with their SHA markers, and invokes
  Claude zero times.
- **AC-7** Neither prompt template contains any instruction that mentions
  the SHA marker. The marker is only written by Python.
- **AC-8** The `update-project-claude-files.md` template no longer exists.
  Two new templates exist with the names specified above.
- **AC-9** `tests/setup-cmd/test_update_project.py` is updated to exercise
  every branch in CAP-2 through CAP-5 for both files, using
  `fake_runner` / `fake_renderer`. Tests pass.
- **AC-10** Invoking `i2code setup update-project --help` shows the same
  CLI surface as today (no new flags, no removed flags).
- **AC-11** Idempotence: running the command twice consecutively with no
  template changes in between performs zero Claude invocations on the
  second run.
- **AC-12** `uvx pyright --level error src/` passes after the change.
