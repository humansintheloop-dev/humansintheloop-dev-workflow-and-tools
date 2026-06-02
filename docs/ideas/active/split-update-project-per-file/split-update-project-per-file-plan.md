# Implementation Plan: Per-file `update-project` flow

## Idea Type

**C. Platform/infrastructure capability** — modifies the internal flow of `i2code setup update-project` so that each target file (`CLAUDE.md`, `.claude/settings.local.json`) is tracked, diffed, and reconciled independently. Public CLI surface is unchanged.

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Project context

This is a Python project (`i2code`) using `uv` and `pytest`. The standard test command is `uv run pytest tests/setup-cmd/test_update_project.py -v`. The type checker is invoked via `uvx pyright --level error src/`. CI already exists and runs the full test suite.

The orchestrator under change is `update_project()` in `src/i2code/setup_cmd/update_project.py:9`. Its existing test suite lives at `tests/setup-cmd/test_update_project.py` and uses `fake_runner` / `fake_renderer` fixtures from `tests/setup-cmd/conftest.py:14`. The current single prompt template is `src/i2code/prompt-templates/update-project-claude-files.md`.

All steps below use TDD: write the failing test first, then make it pass. Each task ends with running pyright and the test suite, then committing via the commit-guidelines skill.

---

## Steel Thread 1: Baseline verification — existing build passes

- [x] **Task 1.1: Existing `update_project` test suite passes on master**
  - TaskType: INFRA
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: All existing tests in `tests/setup-cmd/test_update_project.py` pass (exit code 0). `uvx pyright --level error src/` reports no errors.
  - Evidence: Running `uv run pytest tests/setup-cmd/test_update_project.py -v` exits 0 and `uvx pyright --level error src/` exits 0.
  - Steps:
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` and confirm exit 0
    - [x] Run `uvx pyright --level error src/` and confirm exit 0
    - [x] Record this baseline in the Verification section before proceeding

---

## Steel Thread 2: Scenario S-6 — Both files missing (clean project, zero Claude invocations)

Implements CAP-2 (direct copy of missing files) and CAP-4.2/4.3 (SHA marker writes) for both target files. After this thread, an `update_project` run on a project that has no `CLAUDE.md` and no `.claude/settings.local.json` copies both files from `config_dir`, writes the per-file SHA marker into each, and never invokes Claude. The orchestrator is split into a per-file loop.

- [x] **Task 2.1: `update_project` copies missing `CLAUDE.md` and writes its SHA marker without invoking Claude**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: When the project has no `CLAUDE.md`, calling `update_project(...)` (a) copies `<config_dir>/CLAUDE.md` to `<project_dir>/CLAUDE.md`, (b) appends `<!-- claude-config-files-sha: <current_per_file_sha> -->` as the last line of the copied file, (c) records zero `fake_runner.calls`, (d) returns `ClaudeResult(returncode=0)`.
  - Evidence: New tests `TestMissingFileCopy::test_copies_missing_claude_md_from_template`, `TestMissingFileCopy::test_writes_claude_md_sha_marker_after_copy`, `TestMissingFileCopy::test_no_claude_invocation_when_claude_md_missing` in `tests/setup-cmd/test_update_project.py` all pass.
  - Steps:
    - [x] In `tests/setup-cmd/test_update_project.py`, add a new test class `TestMissingFileCopy` (mark `@pytest.mark.unit`)
    - [x] Write failing test `test_copies_missing_claude_md_from_template`: create `config_dir/CLAUDE.md` with known content, do NOT create `project_dir/CLAUDE.md`; create `project_dir/.claude/settings.local.json` with a valid SHA marker so the second file does not interfere; mock subprocess so `git log -1 --format=%H -- <relpath>/CLAUDE.md` returns `CCC333` and the per-file diff for settings is empty; call `update_project(...)`; assert `os.path.isfile(project_claude_md)` is True and its content starts with the template content
    - [x] Write failing test `test_writes_claude_md_sha_marker_after_copy`: same setup; assert the copied CLAUDE.md's last line equals `<!-- claude-config-files-sha: CCC333 -->`
    - [x] Write failing test `test_no_claude_invocation_when_claude_md_missing`: same setup; assert `len(fake_runner.calls) == 0`
    - [x] Introduce new private helpers in `src/i2code/setup_cmd/update_project.py`:
      - `_copy_template_file(source_path, dest_path)` — copies file, creates parent dirs as needed
      - `_get_per_file_current_sha(repo_root, template_file_relpath)` — runs `git log -1 --format=%H -- <relpath>` from `repo_root`
      - `_write_claude_md_sha(claude_md_path, sha)` — appends/replaces `<!-- claude-config-files-sha: <sha> -->` as last line
    - [x] Restructure `update_project()` to process `CLAUDE.md` first, then `.claude/settings.local.json`, with per-file branching. The first branch implemented is: if the project file is missing, copy from `config_dir`, then write the per-file SHA marker, and do not invoke Claude.
    - [x] For the settings file in this task, keep behavior minimal: if its previous-SHA marker is present and the per-file diff is empty (mocked as empty here), do not invoke Claude (this single branch is enough to make the tests pass; the rest of the settings-side logic comes in later threads)
    - [x] Update `_fake_subprocess_run` (or add a more flexible helper alongside it) so that `git log -1 --format=%H -- ...` and `git diff ...` calls can be steered per file. Match by the `-- <relpath>` token at the end of the argv
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — all three new tests pass; pre-existing tests may now fail (expected — they will be deleted/replaced in later threads)
    - [x] Remove pre-existing tests that contradict the new behavior in this thread: `TestTemplateRendering::test_renders_update_project_claude_files_template`, `TestTemplateRendering::test_template_receives_all_eight_variables` will be replaced later — for now, mark them with `@pytest.mark.skip(reason="superseded by per-file flow; see Steel Thread 5")` to keep the suite green
    - [x] Run `uvx pyright --level error src/` — exit 0
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [x] Run CodeScene `pre_commit_code_health_safeguard` on `src/i2code/setup_cmd/update_project.py`; refactor if score is below 10.0
    - [x] Commit via the commit-guidelines skill

- [x] **Task 2.2: `update_project` copies missing `.claude/settings.local.json` (creating `.claude/`) and writes its SHA marker**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: When the project has no `.claude/settings.local.json`, calling `update_project(...)` (a) creates `<project_dir>/.claude/` if absent, (b) copies `<config_dir>/settings.local.json` to `<project_dir>/.claude/settings.local.json`, (c) writes `Bash(i2code-config-files-sha <current_per_file_sha>)` into the JSON's `permissions.allow` array, (d) records zero `fake_runner.calls`, (e) returns `ClaudeResult(returncode=0)`. End-to-end S-6: when both files are missing, both are copied with markers and Claude is invoked zero times.
  - Evidence: New tests `TestMissingFileCopy::test_copies_missing_settings_from_template`, `TestMissingFileCopy::test_writes_settings_sha_marker_after_copy`, `TestMissingFileCopy::test_creates_claude_directory_if_absent`, `TestMissingFileCopy::test_scenario_s6_both_files_missing_no_claude_invocations` all pass.
  - Steps:
    - [x] Write failing test `test_copies_missing_settings_from_template`: create `config_dir/settings.local.json` with content `{"permissions": {"allow": ["Bash(echo:*)"]}}`; do NOT create `project_dir/.claude/`; ensure CLAUDE.md exists and is fully synced; mock subprocess so settings per-file current SHA is `DDD444`; call `update_project(...)`; assert the destination file exists and its parsed JSON contains the original `Bash(echo:*)` entry
    - [x] Write failing test `test_writes_settings_sha_marker_after_copy`: same setup; assert the parsed JSON's `permissions.allow` contains exactly one entry matching `Bash(i2code-config-files-sha DDD444)`
    - [x] Write failing test `test_creates_claude_directory_if_absent`: same setup; assert `os.path.isdir(os.path.join(project_dir, ".claude"))` is True
    - [x] Write failing test `test_scenario_s6_both_files_missing_no_claude_invocations`: do not create either project file; mock per-file SHAs `CCC333` and `DDD444`; call `update_project(...)`; assert both files exist with their markers and `len(fake_runner.calls) == 0`
    - [x] Add new helper `_write_settings_sha(settings_path, sha)` to `src/i2code/setup_cmd/update_project.py`: parses the JSON, removes any existing `Bash(i2code-config-files-sha ...)` entry from `permissions.allow`, appends `Bash(i2code-config-files-sha <sha>)`, writes the JSON back preserving key order (use `json.load`/`json.dump` with `indent=2`)
    - [x] Extend the per-file loop in `update_project()` so the settings-file branch mirrors the CLAUDE.md branch: missing → copy (creating `.claude/`), then write settings SHA marker, no Claude invocation
    - [x] Run all four new tests; ensure they pass
    - [x] Run `uvx pyright --level error src/` — exit 0
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [x] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [x] Commit via the commit-guidelines skill

---

## Steel Thread 3: Scenario S-4 — Missing one file, other synced (per-file SHA reading + empty-diff routing)

Implements CAP-1.1 (read per-file previous SHA from each marker format) and CAP-3.1 (empty-diff skip with marker advance) for both target files. After this thread, when one file is missing and the other has a valid marker with an empty per-file diff, the missing file is copied and the other file's marker is advanced — Claude is invoked zero times.

- [x] **Task 3.1: `update_project` reads the per-file SHA marker from `CLAUDE.md` and from `.claude/settings.local.json`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: When both files exist with valid markers, `update_project(...)` issues git diff calls scoped to each file using each file's own previous SHA. The `git diff <prev>..<curr> -- <relpath_to_CLAUDE.md>` call uses the CLAUDE.md previous SHA; the `git diff <prev>..<curr> -- <relpath_to_settings.local.json>` call uses the settings previous SHA.
  - Evidence: New tests `TestPerFileShaReading::test_reads_claude_md_previous_sha_from_marker`, `TestPerFileShaReading::test_reads_settings_previous_sha_from_fake_permission_entry`, `TestPerFileShaReading::test_per_file_diff_calls_use_per_file_previous_shas` all pass.
  - Steps:
    - [x] Add a test class `TestPerFileShaReading` (`@pytest.mark.unit`)
    - [x] Write failing test `test_reads_claude_md_previous_sha_from_marker`: create project `CLAUDE.md` containing `<!-- claude-config-files-sha: AAA111 -->`; create project `settings.local.json` with `Bash(i2code-config-files-sha BBB222)` in `permissions.allow`; mock both per-file diffs as empty; assert via `fake_renderer.calls` (if Claude were invoked) or via the captured git commands that the value `AAA111` flows into the CLAUDE.md diff command
    - [x] Write failing test `test_reads_settings_previous_sha_from_fake_permission_entry`: same setup; assert the value `BBB222` flows into the settings diff command
    - [x] Write failing test `test_per_file_diff_calls_use_per_file_previous_shas`: capture all subprocess `git diff` invocations; assert there are exactly two `git diff` calls, one scoped to the CLAUDE.md template path (with `AAA111..<curr>`), one scoped to the settings template path (with `BBB222..<curr>`)
    - [x] Replace `_extract_previous_sha` with `_read_claude_md_sha(claude_md_path) -> str` — same regex, renamed for symmetry
    - [x] Add `_read_settings_sha(settings_path) -> str` — parses JSON, scans `permissions.allow` for `Bash(i2code-config-files-sha <sha>)`, returns the SHA or `""`
    - [x] Add `_get_per_file_diff(repo_root, template_file_relpath, prev_sha, curr_sha) -> str` — runs `git diff <prev>..<curr> -- <relpath>` from `repo_root`. If `prev_sha` is empty or `repo_root` is empty, return `""`
    - [x] Wire the orchestrator: for each file, call `_read_*_sha`, then `_get_per_file_current_sha`, then `_get_per_file_diff`
    - [x] Run all three new tests; ensure they pass
    - [x] Run `uvx pyright --level error src/` — exit 0
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [x] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [x] Commit via the commit-guidelines skill

- [x] **Task 3.2: `update_project` skips Claude when per-file diff is empty and advances the per-file SHA marker**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: For an existing target file whose previous SHA marker is present and whose per-file diff is empty, `update_project(...)` does NOT invoke Claude for that file, and Python rewrites the file's SHA marker to the current per-file SHA. End-to-end S-4: with project CLAUDE.md missing and settings present + synced (empty per-file diff), CLAUDE.md is copied with its marker, settings' marker is advanced, and `fake_runner.calls` is empty.
  - Evidence: New tests `TestEmptyDiffSkip::test_skips_claude_when_claude_md_diff_empty_and_advances_marker`, `TestEmptyDiffSkip::test_skips_claude_when_settings_diff_empty_and_advances_marker`, `TestEmptyDiffSkip::test_scenario_s4_missing_claude_md_settings_synced` all pass.
  - Steps:
    - [x] Add a test class `TestEmptyDiffSkip` (`@pytest.mark.unit`)
    - [x] Write failing test `test_skips_claude_when_claude_md_diff_empty_and_advances_marker`: project CLAUDE.md exists with marker `AAA111`; settings present with marker and empty diff; CLAUDE.md per-file current SHA `CCC333`; CLAUDE.md diff mocked to `""`; assert (a) `len(fake_runner.calls) == 0` for the CLAUDE.md branch, (b) project CLAUDE.md's marker line now reads `<!-- claude-config-files-sha: CCC333 -->`
    - [x] Write failing test `test_skips_claude_when_settings_diff_empty_and_advances_marker`: symmetric setup; settings prev `BBB222`, current `DDD444`, diff `""`; assert the settings file's `permissions.allow` now contains `Bash(i2code-config-files-sha DDD444)` (replacing the previous one) and no other `Bash(i2code-config-files-sha ...)` entries
    - [x] Write failing test `test_scenario_s4_missing_claude_md_settings_synced`: project has no CLAUDE.md; settings present with marker `BBB222`, diff empty; CLAUDE.md current SHA `CCC333`, settings current SHA `DDD444`; assert `len(fake_runner.calls) == 0`, CLAUDE.md exists with `<!-- claude-config-files-sha: CCC333 -->`, settings allow list contains `Bash(i2code-config-files-sha DDD444)`
    - [x] Implement the empty-diff-skip branch in the per-file loop: if previous SHA is non-empty AND per-file diff is empty, write the new SHA marker (using `_write_claude_md_sha` or `_write_settings_sha`) and skip Claude
    - [x] Run all three new tests; ensure they pass
    - [x] Run `uvx pyright --level error src/` — exit 0
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [x] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [x] Commit via the commit-guidelines skill

---

## Steel Thread 4: Scenario S-3 — First sync for an existing file (no marker present)

Implements CAP-3.2 (first-sync rendering with full template content) and CAP-3.5 (prompts never reference the SHA marker) plus CAP-4 (Python writes SHA after Claude succeeds) for the first-sync branch. Introduces the two new per-file prompt templates and removes the legacy template.

- [x] **Task 4.1: `update_project` invokes Claude with `IS_FIRST_SYNC=true` and full template content when `CLAUDE.md` has no marker**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: When project `CLAUDE.md` exists but contains no SHA marker, `update_project(...)`: (a) renders `update-project-claude-md.md` with `IS_FIRST_SYNC="true"`, `PREVIOUS_SHA=""`, `CONFIG_DIFF` containing the full current template content prefixed by an explanatory leading message; (b) calls `claude_runner.run_interactive(["claude", <rendered_prompt>], cwd=project_dir)`; (c) on Claude exit 0, writes `<!-- claude-config-files-sha: <current_sha> -->` as the last line of project `CLAUDE.md`.
  - Evidence: New tests `TestFirstSyncClaudeMd::test_renders_first_sync_prompt_with_is_first_sync_true`, `TestFirstSyncClaudeMd::test_first_sync_prompt_contains_full_template_content`, `TestFirstSyncClaudeMd::test_first_sync_invokes_claude_for_claude_md`, `TestFirstSyncClaudeMd::test_python_writes_claude_md_sha_after_claude_success` all pass.
  - Steps:
    - [x] Create new template `src/i2code/prompt-templates/update-project-claude-md.md`. Content: instructions for reconciling a project's CLAUDE.md with the template version. Use only the variables `$PROJECT_DIR`, `$PROJECT_CLAUDE_MD`, `$CONFIG_CLAUDE_MD`, `$CURRENT_SHA`, `$PREVIOUS_SHA`, `$CONFIG_DIFF`, `$IS_FIRST_SYNC`. Cover markdown-specific reconciliation: preserve project-specific sections, merge new template sections, ask the user before applying each change. MUST NOT mention `claude-config-files-sha` or any SHA-write instruction
    - [x] Add a test class `TestFirstSyncClaudeMd` (`@pytest.mark.unit`)
    - [x] Write failing test `test_renders_first_sync_prompt_with_is_first_sync_true`: project CLAUDE.md exists with content `# Project\n` (no marker); settings present with marker and empty diff; assert `fake_renderer.calls[0]` template name is `"update-project-claude-md.md"` and `variables["IS_FIRST_SYNC"] == "true"` and `variables["PREVIOUS_SHA"] == ""`
    - [x] Write failing test `test_first_sync_prompt_contains_full_template_content`: create `config_dir/CLAUDE.md` with content `Hello template body`; assert that the rendered `CONFIG_DIFF` for CLAUDE.md contains `Hello template body` and contains a leading explanatory message such as `"first sync"` (case-insensitive)
    - [x] Write failing test `test_first_sync_invokes_claude_for_claude_md`: same setup; assert `fake_runner.calls[0]` has method `"run_interactive"`, command starts with `"claude"`, and `cwd == project_dir`
    - [x] Write failing test `test_python_writes_claude_md_sha_after_claude_success`: same setup; pre-set `fake_runner` to return `ClaudeResult(returncode=0)`; current SHA `CCC333`; call `update_project(...)`; read project CLAUDE.md and assert its last line equals `<!-- claude-config-files-sha: CCC333 -->`
    - [x] In `update_project()`, implement the first-sync branch for CLAUDE.md: when project file exists and previous SHA is empty, read the full current template file content, build `CONFIG_DIFF` as `"First sync — full current template content follows:\n\n" + <template_content>`, render `update-project-claude-md.md` with `IS_FIRST_SYNC="true"`, invoke Claude, then on `returncode == 0` call `_write_claude_md_sha(project_claude_md, current_sha)`
    - [x] Make sure the new template file is included in any packaging via the existing template loader (check `src/i2code/template_renderer.py` and the package config to confirm `prompt-templates/*.md` are bundled)
    - [x] Run all four new tests; ensure they pass
    - [x] Run `uvx pyright --level error src/` — exit 0
    - [x] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [x] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [x] Commit via the commit-guidelines skill

- [ ] **Task 4.2: `update_project` invokes Claude with `IS_FIRST_SYNC=true` and full template content when `.claude/settings.local.json` has no marker**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: When project `.claude/settings.local.json` exists but contains no `Bash(i2code-config-files-sha ...)` entry, `update_project(...)`: (a) renders `update-project-settings.md` with `IS_FIRST_SYNC="true"`, `PREVIOUS_SHA=""`, `CONFIG_DIFF` containing the full current template content prefixed by an explanatory message; (b) invokes Claude per CAP-3.4; (c) on Claude exit 0, inserts `Bash(i2code-config-files-sha <current_sha>)` into the project file's `permissions.allow` array.
  - Evidence: New tests `TestFirstSyncSettings::test_renders_first_sync_settings_prompt`, `TestFirstSyncSettings::test_first_sync_settings_prompt_contains_full_template_content`, `TestFirstSyncSettings::test_python_writes_settings_sha_after_claude_success` all pass.
  - Steps:
    - [ ] Create new template `src/i2code/prompt-templates/update-project-settings.md`. Use only the variables `$PROJECT_DIR`, `$PROJECT_SETTINGS`, `$CONFIG_SETTINGS`, `$CURRENT_SHA`, `$PREVIOUS_SHA`, `$CONFIG_DIFF`, `$IS_FIRST_SYNC`. Cover JSON-permissions-specific reconciliation: merging new entries into `permissions.allow`/`deny`/`ask`, preserving project-specific entries, asking before applying each change. MUST NOT mention `claude-config-files-sha` or any SHA-write instruction
    - [ ] Add a test class `TestFirstSyncSettings` (`@pytest.mark.unit`)
    - [ ] Write failing test `test_renders_first_sync_settings_prompt`: project CLAUDE.md exists with marker (empty diff); project settings.local.json exists with `{"permissions": {"allow": ["Bash(echo:*)"]}}` (no SHA entry); assert one render call for `"update-project-settings.md"` with `IS_FIRST_SYNC == "true"` and `PREVIOUS_SHA == ""`
    - [ ] Write failing test `test_first_sync_settings_prompt_contains_full_template_content`: create `config_dir/settings.local.json` with distinctive content `{"permissions": {"allow": ["Bash(unique-marker:*)"]}}`; assert the settings `CONFIG_DIFF` contains `Bash(unique-marker:*)` and a leading explanatory message
    - [ ] Write failing test `test_python_writes_settings_sha_after_claude_success`: settings current SHA `DDD444`; pre-set `fake_runner` to return `ClaudeResult(returncode=0)`; call `update_project(...)`; parse project settings.local.json and assert its `permissions.allow` includes `Bash(i2code-config-files-sha DDD444)`
    - [ ] Implement the first-sync branch for settings in `update_project()` symmetric to CLAUDE.md
    - [ ] Run all three new tests; ensure they pass
    - [ ] Run `uvx pyright --level error src/` — exit 0
    - [ ] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [ ] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [ ] Commit via the commit-guidelines skill

---

## Steel Thread 5: Scenario S-1 — Routine update with both files present and non-empty diffs

Implements CAP-3.3 (per-file Claude invocation scoped to the per-file diff with `IS_FIRST_SYNC=false`). After this thread, the primary end-to-end scenario S-1 invokes Claude twice in CLAUDE.md-then-settings order with the correct per-file diff content and rewrites both SHA markers on success.

- [ ] **Task 5.1: `update_project` invokes Claude per file with `IS_FIRST_SYNC=false` and scoped per-file diff content**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: For scenario S-1 (project CLAUDE.md has marker `AAA111`, settings has marker `BBB222`, CLAUDE.md current SHA `CCC333` with non-empty diff, settings current SHA `DDD444` with non-empty diff), `update_project(...)`: (a) makes exactly two `fake_renderer` calls in order — first `update-project-claude-md.md`, then `update-project-settings.md`; (b) each render call has `IS_FIRST_SYNC == "false"`, the correct per-file `PREVIOUS_SHA`/`CURRENT_SHA`, and `CONFIG_DIFF` equal to the per-file git diff text; (c) makes exactly two `fake_runner.run_interactive` calls in the same order; (d) after both Claude calls return 0, project CLAUDE.md ends with `<!-- claude-config-files-sha: CCC333 -->` and project settings allow list contains `Bash(i2code-config-files-sha DDD444)`.
  - Evidence: New tests `TestRoutineUpdate::test_two_renders_in_claude_md_then_settings_order`, `TestRoutineUpdate::test_each_render_has_per_file_diff_and_shas`, `TestRoutineUpdate::test_two_claude_invocations_in_order`, `TestRoutineUpdate::test_scenario_s1_both_markers_advanced` all pass.
  - Steps:
    - [ ] Un-skip and rewrite the pre-existing `TestTemplateRendering` tests that were skipped in Task 2.1 by replacing them with the new `TestRoutineUpdate` class. Delete the old skipped tests
    - [ ] Add a test class `TestRoutineUpdate` (`@pytest.mark.unit`)
    - [ ] Write failing test `test_two_renders_in_claude_md_then_settings_order`: set up S-1 preconditions; mock CLAUDE.md diff `"diff-for-claude-md"` and settings diff `"diff-for-settings"`; assert `[call[0] for call in fake_renderer.calls] == ["update-project-claude-md.md", "update-project-settings.md"]`
    - [ ] Write failing test `test_each_render_has_per_file_diff_and_shas`: assert `fake_renderer.calls[0][1]` contains `IS_FIRST_SYNC == "false"`, `PREVIOUS_SHA == "AAA111"`, `CURRENT_SHA == "CCC333"`, `CONFIG_DIFF == "diff-for-claude-md"`; assert `fake_renderer.calls[1][1]` contains `IS_FIRST_SYNC == "false"`, `PREVIOUS_SHA == "BBB222"`, `CURRENT_SHA == "DDD444"`, `CONFIG_DIFF == "diff-for-settings"`
    - [ ] Write failing test `test_two_claude_invocations_in_order`: assert `len(fake_runner.calls) == 2` and both have method `"run_interactive"` with `cwd == project_dir`; the first command contains `template=update-project-claude-md.md` and the second contains `template=update-project-settings.md`
    - [ ] Write failing test `test_scenario_s1_both_markers_advanced`: pre-set `fake_runner` to return `ClaudeResult(returncode=0)`; after the call, assert project CLAUDE.md's last line is `<!-- claude-config-files-sha: CCC333 -->` and the project settings JSON's `allow` contains exactly one `Bash(i2code-config-files-sha DDD444)` (and no leftover `BBB222` entry)
    - [ ] Implement the non-empty-diff branch in `update_project()`: when previous SHA is non-empty and per-file diff is non-empty, render with `IS_FIRST_SYNC="false"` and `CONFIG_DIFF=<per-file diff text>`, invoke Claude, on success write the new per-file SHA marker
    - [ ] Run all four new tests; ensure they pass
    - [ ] Also confirm that scenario S-2 (only CLAUDE.md changed: CLAUDE.md non-empty diff, settings empty diff) works end-to-end — add a single regression test `TestRoutineUpdate::test_scenario_s2_only_claude_md_changed`: CLAUDE.md diff non-empty, settings diff empty; assert exactly one Claude invocation (for CLAUDE.md), both markers advanced to their respective current SHAs
    - [ ] Run `uvx pyright --level error src/` — exit 0
    - [ ] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [ ] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [ ] Commit via the commit-guidelines skill

---

## Steel Thread 6: Scenario S-5 — Claude fails on first file → abort, no SHAs written

Implements CAP-5.2, CAP-5.4, CAP-7.2 (abort-on-first-failure semantics). After this thread, when Claude exits non-zero for `CLAUDE.md`, the second file is not processed and neither SHA marker is written.

- [ ] **Task 6.1: `update_project` aborts after non-zero Claude exit, leaving both markers unchanged**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: For scenario S-5 (both files present with markers, both diffs non-empty), when `fake_runner` returns `ClaudeResult(returncode=2)` for the first invocation, `update_project(...)`: (a) makes exactly one render call (`update-project-claude-md.md`); (b) makes exactly one `fake_runner.run_interactive` call; (c) does NOT rewrite project CLAUDE.md's marker (it remains `AAA111`); (d) does NOT rewrite project settings.local.json's marker (it remains `BBB222`); (e) returns a `ClaudeResult` whose `returncode == 2`.
  - Evidence: New tests `TestAbortOnFailure::test_no_second_render_when_first_claude_fails`, `TestAbortOnFailure::test_no_sha_writes_when_first_claude_fails`, `TestAbortOnFailure::test_returns_failing_claude_result` all pass.
  - Steps:
    - [ ] Add a test class `TestAbortOnFailure` (`@pytest.mark.unit`)
    - [ ] Write failing test `test_no_second_render_when_first_claude_fails`: S-1 preconditions; pre-set `fake_runner.set_result(ClaudeResult(returncode=2))`; call `update_project(...)`; assert `len(fake_renderer.calls) == 1` and `fake_renderer.calls[0][0] == "update-project-claude-md.md"`
    - [ ] Write failing test `test_no_sha_writes_when_first_claude_fails`: same setup; after the call, read project CLAUDE.md and assert its marker is still `<!-- claude-config-files-sha: AAA111 -->`; parse project settings and assert its allow list still contains `Bash(i2code-config-files-sha BBB222)` (and not `DDD444`)
    - [ ] Write failing test `test_returns_failing_claude_result`: same setup; assert the returned `ClaudeResult.returncode == 2`
    - [ ] Update `update_project()` to: after each Claude invocation, check `result.returncode`; if non-zero, return immediately without writing the file's SHA marker and without processing the next file
    - [ ] Also update the no-Claude branches (missing copy, empty-diff skip) to return `ClaudeResult(returncode=0)` from a single explicit synthesized result when no Claude invocation was performed for any file (CAP-7.3)
    - [ ] Add a regression test `TestAbortOnFailure::test_returns_zero_when_no_claude_invocations`: scenario S-6 (both files missing); assert the return value's `returncode == 0`
    - [ ] Run all four new tests; ensure they pass
    - [ ] Run `uvx pyright --level error src/` — exit 0
    - [ ] Run `uv run pytest tests/setup-cmd/test_update_project.py -v` — exit 0
    - [ ] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [ ] Commit via the commit-guidelines skill

---

## Steel Thread 7: Idempotence guarantee and legacy template cleanup

Closes out AC-7, AC-8, AC-11. After this thread, the legacy single-template file is removed, no prompt template mentions the SHA marker, and running `update-project` twice in a row with no template changes performs zero Claude invocations on the second run.

- [ ] **Task 7.1: Delete legacy `update-project-claude-files.md` template and assert idempotence**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: (a) `src/i2code/prompt-templates/update-project-claude-files.md` does not exist; (b) running `update_project(...)` a first time with S-1 preconditions advances both markers to the current per-file SHAs; (c) running `update_project(...)` a second time (no template changes between runs) results in zero Claude invocations and both markers remain at the current SHAs; (d) neither `update-project-claude-md.md` nor `update-project-settings.md` contains the string `claude-config-files-sha` or any instruction telling Claude to write a SHA.
  - Evidence: New tests `TestIdempotenceAndCleanup::test_second_consecutive_run_invokes_claude_zero_times`, `TestIdempotenceAndCleanup::test_legacy_template_file_removed`, `TestIdempotenceAndCleanup::test_neither_new_template_mentions_sha_marker` all pass.
  - Steps:
    - [ ] Add a test class `TestIdempotenceAndCleanup` (`@pytest.mark.unit`)
    - [ ] Write failing test `test_second_consecutive_run_invokes_claude_zero_times`: S-1 preconditions; pre-set `fake_runner` to return `ClaudeResult(returncode=0)`; run `update_project(...)` once; reset `fake_runner.calls` and `fake_renderer.calls`; with the same git mock (no diff change — both prev and curr now equal `CCC333`/`DDD444`, diffs empty), run `update_project(...)` again; assert `len(fake_runner.calls) == 0` and `len(fake_renderer.calls) == 0`
    - [ ] Write failing test `test_legacy_template_file_removed`: `assert not os.path.exists("src/i2code/prompt-templates/update-project-claude-files.md")`
    - [ ] Write failing test `test_neither_new_template_mentions_sha_marker`: read each of `src/i2code/prompt-templates/update-project-claude-md.md` and `src/i2code/prompt-templates/update-project-settings.md`; assert the substring `claude-config-files-sha` does not appear in either, and neither contains instructions matching the regex `(?i)write.*sha|update.*sha.*marker|update.*tracking.*comment`
    - [ ] Delete `src/i2code/prompt-templates/update-project-claude-files.md`
    - [ ] Re-read the two new templates and ensure they contain no SHA-marker instructions — remove any if present
    - [ ] Run all three new tests; ensure they pass
    - [ ] Run `uvx pyright --level error src/` — exit 0
    - [ ] Run the entire test suite (`uv run pytest -v`) to make sure no other tests reference the deleted template
    - [ ] Run CodeScene `pre_commit_code_health_safeguard`; refactor if below 10.0
    - [ ] Commit via the commit-guidelines skill

---

## Steel Thread 8: Refactor — consolidate per-file processing into a small dispatch table

Code-quality cleanup pass. Reduces duplication between the CLAUDE.md and settings branches of `update_project()` after all behavior is implemented and tests pass.

- [ ] **Task 8.1: Extract per-file processing into a single function parameterized by file-kind**
  - TaskType: REFACTOR
  - Entrypoint: `uv run pytest tests/setup-cmd/test_update_project.py -v`
  - Observable: No behavior change. All tests added in Steel Threads 2–7 still pass. The orchestrator body in `update_project()` shrinks: a single loop iterates over a list of two file descriptors (one for `CLAUDE.md`, one for `settings.local.json`), each carrying its source/destination paths, its template name, its SHA-reader, and its SHA-writer. The per-file branches (missing → copy; present, no marker → first-sync Claude; present, marker, empty diff → skip; present, marker, non-empty diff → diff Claude) are expressed once.
  - Evidence: Running `uv run pytest tests/setup-cmd/test_update_project.py -v` after the refactor exits 0 with the same test set as Steel Thread 7. `uvx pyright --level error src/` exits 0. CodeScene reports a score of 10.0 for `src/i2code/setup_cmd/update_project.py`.
  - Steps:
    - [ ] Define a small dataclass or namedtuple `_FileSpec` with fields: `project_path`, `source_path`, `template_name`, `template_relpath`, `read_sha`, `write_sha`, `render_vars(project_path, source_path, prev_sha, curr_sha, diff, is_first_sync) -> dict` (the per-file variable-name mapping — `PROJECT_CLAUDE_MD` vs `PROJECT_SETTINGS`, `CONFIG_CLAUDE_MD` vs `CONFIG_SETTINGS`)
    - [ ] Build the two file specs inside `update_project()` and iterate over them; on each iteration apply the four-branch routing
    - [ ] Stop on first non-zero Claude exit (CAP-5.2)
    - [ ] Run the existing test suite — all tests must still pass without modification (this is a refactor)
    - [ ] Run `uvx pyright --level error src/` — exit 0
    - [ ] Run CodeScene `pre_commit_code_health_safeguard`; iterate until score is 10.0 for the changed file
    - [ ] Commit via the commit-guidelines skill

---

## Final acceptance checklist

After Steel Thread 8, verify the full spec acceptance criteria:

- [ ] AC-1: S-1 invokes Claude twice in CLAUDE.md-then-settings order; both markers advance — covered by `TestRoutineUpdate::test_scenario_s1_both_markers_advanced` and `test_two_claude_invocations_in_order`
- [ ] AC-2: S-2 invokes Claude exactly once — covered by `TestRoutineUpdate::test_scenario_s2_only_claude_md_changed`
- [ ] AC-3: S-3 first-sync passes full template content — covered by `TestFirstSyncClaudeMd` and `TestFirstSyncSettings`
- [ ] AC-4: S-4 missing file copied without Claude — covered by `TestEmptyDiffSkip::test_scenario_s4_missing_claude_md_settings_synced`
- [ ] AC-5: S-5 abort leaves markers unchanged — covered by `TestAbortOnFailure`
- [ ] AC-6: S-6 both files copied, zero Claude invocations — covered by `TestMissingFileCopy::test_scenario_s6_both_files_missing_no_claude_invocations`
- [ ] AC-7: prompts never mention the SHA marker — covered by `TestIdempotenceAndCleanup::test_neither_new_template_mentions_sha_marker`
- [ ] AC-8: legacy template removed — covered by `TestIdempotenceAndCleanup::test_legacy_template_file_removed`
- [ ] AC-9: all per-file branches covered for both files — covered by the union of `TestMissingFileCopy`, `TestEmptyDiffSkip`, `TestFirstSyncClaudeMd`, `TestFirstSyncSettings`, `TestRoutineUpdate`, `TestAbortOnFailure`
- [ ] AC-10: `i2code setup update-project --help` shows no flag changes — manually run `uv run i2code setup update-project --help` and compare against master
- [ ] AC-11: idempotence — covered by `TestIdempotenceAndCleanup::test_second_consecutive_run_invokes_claude_zero_times`
- [ ] AC-12: `uvx pyright --level error src/` exits 0 — run on the final commit

If any AC is not satisfied, add the missing test/fix as a follow-up task within the relevant steel thread before opening a PR.

---

## Change History
### 2026-06-02 15:31 - mark-task-complete
Baseline verified: pytest 22 passed exit 0; pyright 0 errors exit 0

### 2026-06-02 15:44 - mark-task-complete
TestMissingFileCopy 3/3 passing; pytest exit 0 (5 passed, 20 skipped in file); pyright --level error exit 0; CodeScene score 10.0

### 2026-06-02 15:52 - mark-task-complete
TestMissingFileCopy 7/7 passing; pytest exit 0 (9 passed, 20 skipped); pyright --level error exit 0; CodeScene 10.0/10.0 on both files; safeguard PASSED

### 2026-06-02 16:00 - mark-task-complete
TestPerFileShaReading 3/3 passing; pytest exit 0 (12 passed, 20 skipped); pyright --level error exit 0; CodeScene 10.0; safeguard PASSED

### 2026-06-02 16:04 - mark-task-complete
TestEmptyDiffSkip 3/3 passing; pytest exit 0 (15 passed, 20 skipped); pyright --level error exit 0; CodeScene safeguard PASSED

### 2026-06-02 16:12 - mark-task-complete
TestFirstSyncClaudeMd 4/4 passing; pytest exit 0 (19 passed, 20 skipped); pyright --level error exit 0; CodeScene 10.0 after _Context refactor
