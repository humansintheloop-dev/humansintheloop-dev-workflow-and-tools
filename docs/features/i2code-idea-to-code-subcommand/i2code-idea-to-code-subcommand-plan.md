Now I have a thorough understanding of the codebase. Let me generate the plan.

---

# Implementation Plan: Package Workflow Scripts as i2code Subcommands

## Idea Type

**C. Platform/infrastructure capability** — This packages existing workflow shell scripts as installable CLI subcommands, making the entire idea-to-code workflow accessible via a single `uv`-installable `i2code` CLI.

---

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

## Overview

This plan packages 13 shell scripts from `workflow-scripts/` as `i2code` subcommands across three new Click groups (`idea-to-plan`, `improve`, `setup`). The scripts remain as shell scripts but are bundled as package data under `src/i2code/scripts/` and `src/i2code/prompt-templates/`, with thin Click wrappers that invoke them via `subprocess.run()`. A shared `script_runner.py` module handles script location, executability, and exit code propagation.

**Key architectural decisions:**
- `src/i2code/script_runner.py` — shared utility that resolves bundled script paths using `Path(__file__).parent / "scripts"`, ensures execute permission, and runs scripts via `subprocess.run()`
- Click wrappers accept all arguments as unprocessed (`nargs=-1, type=click.UNPROCESSED`) and forward them to the shell script without parsing
- Tests mock `subprocess.run` to verify correct script invocation without actually executing shell scripts (which require `claude` CLI, interactive terminal, etc.)
- Smoke tests validate CLI discoverability (`--help` output at group and per-subcommand level) and are run by CI via `test-scripts/test-end-to-end.sh`

**Test approach:**
- Unit tests: pytest with `CliRunner` and mocked `subprocess.run` in `tests/script-runner/` and `tests/idea-to-plan/`, `tests/improve/`, `tests/setup-cmd/`
- Smoke tests: shell script `test-scripts/test-subcommands-smoke.sh` validating `--help` output for all groups and each individual subcommand (exits 0)
- CI: existing `test-scripts/test-end-to-end.sh` runs both pytest (via `test-unit.sh`) and smoke tests
- Each test directory needs a `conftest.py` that marks tests as `unit` (following the pattern in `tests/plan-manager/conftest.py`)

**Steps should be implemented using TDD** — write a failing test for each piece of behavior before implementing the production code.

---

## Steel Thread 1: Script Runner Infrastructure and First Working Subcommand

Proves that shell scripts can be bundled as package data, located at runtime, invoked via Click CLI wrapper, and validated by CI.

- [x] **Task 1.1: Script runner locates bundled script, forwards arguments, and propagates exit code**
  - TaskType: INFRA
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/script-runner/ -v -m unit`
  - Observable: `run_script("brainstorm-idea.sh", ["my-dir"])` resolves the path to `src/i2code/scripts/brainstorm-idea.sh`, ensures execute permission, calls `subprocess.run` with `[resolved_path, "my-dir"]`, and returns the subprocess result. Raises an error for scripts that do not exist in the bundle.
  - Evidence: pytest tests pass with exit code 0
  - Steps:
    - [x] Copy all 14 in-scope shell scripts from `workflow-scripts/` to `src/i2code/scripts/`: `_helper.sh`, `brainstorm-idea.sh`, `idea-to-code.sh`, `make-spec.sh`, `make-plan.sh`, `revise-spec.sh`, `revise-plan.sh`, `create-design-doc.sh`, `analyze-sessions.sh`, `create-summary-reports.sh`, `review-issues.sh`, `update-claude-files-from-project.sh`, `setup-claude-files.sh`, `update-project-claude-files.sh`
    - [x] Copy all 10 prompt templates from `prompt-templates/` to `src/i2code/prompt-templates/`: `brainstorm-idea.md`, `create-spec.md`, `create-implementation-plan.md`, `revise-plan.md`, `create-design-doc.md`, `analyze-sessions.md`, `create-summary-report.md`, `review-issues.md`, `update-claude-files-from-project.md`, `update-project-claude-files.md`
    - [x] Update `pyproject.toml` `[tool.hatch.build.targets.wheel]` to include `scripts/` and `prompt-templates/` directories as package data (they are already under `src/i2code/` which is in `packages`)
    - [x] Create `src/i2code/script_runner.py` with `run_script(script_name, args=())` that: resolves path via `Path(__file__).parent / "scripts" / script_name`, raises `FileNotFoundError` if missing, ensures execute permission via `os.chmod`, calls `subprocess.run([str(script_path)] + list(args))`, and returns the `CompletedProcess` result
    - [x] Create `tests/script-runner/__init__.py` and `tests/script-runner/conftest.py` (mark tests as `unit`)
    - [x] Create `tests/script-runner/test_script_runner.py` with tests: resolves correct path, ensures executability, forwards arguments to subprocess, returns subprocess result, raises error for missing script

- [ ] **Task 1.2: `i2code idea-to-plan brainstorm <dir>` invokes bundled brainstorm-idea.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan brainstorm my-dir`
  - Observable: The command locates `brainstorm-idea.sh` from bundled package data, invokes it via `subprocess.run` with `["my-dir"]` as arguments, and exits with the script's exit code
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies `brainstorm-idea.sh` is invoked with correct arguments and exit code is propagated
  - Steps:
    - [ ] Create `src/i2code/idea_to_plan/__init__.py`
    - [ ] Create `src/i2code/idea_to_plan/cli.py` with Click group `idea_to_plan` (command name `"idea-to-plan"`, help text `"Develop an idea into an implementation plan."`) and `brainstorm_cmd` that accepts `args` via `@click.argument("args", nargs=-1, type=click.UNPROCESSED)`, calls `run_script("brainstorm-idea.sh", args)`, and exits with the result's return code
    - [ ] Register `idea_to_plan` group in `src/i2code/cli.py` via `main.add_command(idea_to_plan)`
    - [ ] Create `tests/idea-to-plan/__init__.py` and `tests/idea-to-plan/conftest.py` (mark tests as `unit`)
    - [ ] Create `tests/idea-to-plan/test_brainstorm_cli.py` that uses `CliRunner` and mocks `subprocess.run` to verify correct invocation

- [ ] **Task 1.3: CLI smoke tests validate idea-to-plan group and brainstorm subcommand are discoverable**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code --help` lists `idea-to-plan` group; `i2code idea-to-plan --help` lists `brainstorm` subcommand with its help text
  - Evidence: `test-scripts/test-subcommands-smoke.sh` passes within `test-end-to-end.sh`; CI runs `test-end-to-end.sh` and passes
  - Steps:
    - [ ] Create `test-scripts/test-subcommands-smoke.sh` that verifies `uv run i2code --help` contains `idea-to-plan`, `uv run i2code idea-to-plan --help` contains `brainstorm`, and `uv run i2code idea-to-plan brainstorm --help` exits 0 (follow the pattern in `test-scripts/test-plan-cli-smoke.sh`)
    - [ ] Add `"$SCRIPT_DIR/test-subcommands-smoke.sh"` to `test-scripts/test-end-to-end.sh` after the plan CLI smoke tests line

---

- [ ] **Task 1.4: Remove migrated `brainstorm-idea.sh` from `workflow-scripts/`**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `workflow-scripts/brainstorm-idea.sh` is removed from the repository. All tests continue to pass since the bundled copy in `src/i2code/scripts/` is used by the `i2code idea-to-plan brainstorm` subcommand.
  - Evidence: `test-end-to-end.sh passes; `workflow-scripts/brainstorm-idea.sh` no longer exists`
  - Steps:
    - [ ] Run `git rm workflow-scripts/brainstorm-idea.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Steel Thread 2: Complete idea-to-plan Subcommands

Completes the `idea-to-plan` group with all remaining subcommands, including skill discovery modifications for `make-plan` and `design-doc`.

- [ ] **Task 2.1: `i2code idea-to-plan spec`, `revise-spec`, and `revise-plan` subcommands invoke their respective scripts**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan spec my-dir`
  - Observable: Each subcommand locates its corresponding bundled script (`make-spec.sh`, `revise-spec.sh`, `revise-plan.sh`), forwards all arguments, and propagates exit code. `spec` and `revise-plan` also forward additional `claude-args`.
  - Evidence: pytest tests using `CliRunner` with mocked `subprocess.run` verify correct script invocation for each subcommand; smoke test updated to verify all three appear in `i2code idea-to-plan --help`
  - Steps:
    - [ ] Add `spec_cmd`, `revise_spec_cmd`, and `revise_plan_cmd` to `src/i2code/idea_to_plan/cli.py`, each following the brainstorm pattern (script names: `make-spec.sh`, `revise-spec.sh`, `revise-plan.sh`)
    - [ ] Create `tests/idea-to-plan/test_spec_cli.py`, `tests/idea-to-plan/test_revise_spec_cli.py`, `tests/idea-to-plan/test_revise_plan_cli.py` — verify each one incrementally before creating the next
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `spec`, `revise-spec`, and `revise-plan` in `idea-to-plan --help`, and verify `uv run i2code idea-to-plan spec --help`, `revise-spec --help`, and `revise-plan --help` each exit 0

- [ ] **Task 2.2: Skill discovery helper `list-plugin-skills.sh` and `i2code idea-to-plan make-plan` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan make-plan my-dir`
  - Observable: `list-plugin-skills.sh` searches `~/.claude/plugins/cache/` for the `idea-to-code` plugin, lists subdirectory names under its `skills/` directory, and outputs them as `idea-to-code:<skill-name>` comma-separated. If the plugin is not installed, it prints a warning to stderr and outputs an empty string. `make-plan.sh` (in `src/i2code/scripts/`) calls `list-plugin-skills.sh` instead of `ls -1 "$DIR/../skills"`. The `make-plan` subcommand invokes modified `make-plan.sh` and propagates exit code.
  - Evidence: pytest test for `make-plan` subcommand verifies script invocation; shell test script validates `list-plugin-skills.sh` outputs correct format when plugin exists and outputs empty string with warning when plugin is absent
  - Steps:
    - [ ] Create `src/i2code/scripts/list-plugin-skills.sh` that: searches `~/.claude/plugins/cache/` for a directory matching `*idea-to-code*/skills/`, lists subdirectory names, formats as `idea-to-code:<name>` comma-separated, prints warning to stderr and outputs empty string if not found
    - [ ] Modify `src/i2code/scripts/make-plan.sh` to replace `ls -1 "$DIR/../skills" | sed ...` with a call to `$DIR/list-plugin-skills.sh`
    - [ ] Add `make_plan_cmd` to `src/i2code/idea_to_plan/cli.py`
    - [ ] Create `tests/idea-to-plan/test_make_plan_cli.py`
    - [ ] Create `test-scripts/test-list-plugin-skills.sh` that validates output format (add to `test-end-to-end.sh`)
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `make-plan` in `idea-to-plan --help`, and verify `uv run i2code idea-to-plan make-plan --help` exits 0

- [ ] **Task 2.3: `i2code idea-to-plan design-doc` subcommand with skill discovery**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan design-doc my-dir`
  - Observable: `create-design-doc.sh` (in `src/i2code/scripts/`) calls `list-plugin-skills.sh` instead of `ls -1 "$DIR/../skills"`. The `design-doc` subcommand invokes modified `create-design-doc.sh` and propagates exit code.
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies `create-design-doc.sh` is invoked with correct arguments
  - Steps:
    - [ ] Modify `src/i2code/scripts/create-design-doc.sh` to replace `ls -1 "$DIR/../skills" | sed ...` with a call to `$DIR/list-plugin-skills.sh`
    - [ ] Add `design_doc_cmd` to `src/i2code/idea_to_plan/cli.py`
    - [ ] Create `tests/idea-to-plan/test_design_doc_cli.py`
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `design-doc` in `idea-to-plan --help`, and verify `uv run i2code idea-to-plan design-doc --help` exits 0

- [ ] **Task 2.4: Modify `idea-to-code.sh` to call `i2code implement` instead of `implement-plan.sh`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan run my-dir`
  - Observable: `idea-to-code.sh` (in `src/i2code/scripts/`) replaces all references to `$SCRIPT_DIR/implement-plan.sh` with `i2code implement`. The "Implement the entire plan" menu option calls `i2code implement "$dir"` and the "Implement a specific task" option is removed (since `i2code implement` does not accept a task argument). The orchestrator no longer depends on `implement-plan.sh` being present in the scripts bundle.
  - Evidence: `Manual review of modified `idea-to-code.sh` confirms no remaining references to `implement-plan.sh`; the `run` subcommand smoke test passes`
  - Steps:
    - [ ] Modify `src/i2code/scripts/idea-to-code.sh` to replace `"$SCRIPT_DIR/implement-plan.sh" "$dir"` (line 267) with `i2code implement "$dir"`
    - [ ] Remove the "Implement a specific task" menu option (lines 289-317) since `i2code implement` does not support a task argument — renumber the Exit option accordingly
    - [ ] Update the `handle_error` call for implement to reference `i2code implement` instead of `$SCRIPT_DIR/implement-plan.sh`
- [ ] **Task 2.5: `i2code idea-to-plan run` subcommand invokes the orchestrator**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan run my-dir`
  - Observable: The `run` subcommand invokes `idea-to-code.sh` with all forwarded arguments and propagates exit code
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies `idea-to-code.sh` is invoked with correct arguments
  - Steps:
    - [ ] Add `run_cmd` to `src/i2code/idea_to_plan/cli.py` (script: `idea-to-code.sh`)
    - [ ] Create `tests/idea-to-plan/test_run_cli.py`
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `run` in `idea-to-plan --help`, and verify `uv run i2code idea-to-plan run --help` exits 0

---

- [ ] **Task 2.6: Remove migrated idea-to-plan scripts from `workflow-scripts/`**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `workflow-scripts/make-spec.sh`, `revise-spec.sh`, `revise-plan.sh`, `make-plan.sh`, `create-design-doc.sh`, and `idea-to-code.sh` are removed from the repository. All tests continue to pass.
  - Evidence: `test-end-to-end.sh passes; listed scripts no longer exist in `workflow-scripts/``
  - Steps:
    - [ ] Run `git rm workflow-scripts/make-spec.sh workflow-scripts/revise-spec.sh workflow-scripts/revise-plan.sh workflow-scripts/make-plan.sh workflow-scripts/create-design-doc.sh workflow-scripts/idea-to-code.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Steel Thread 3: improve Subcommands

Adds the `improve` group with four subcommands for session analysis, summary reports, issue review, and Claude file updates.

- [ ] **Task 3.1: `i2code improve analyze-sessions`, `summary-reports`, and `review-issues` subcommands**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve analyze-sessions my-tracking-dir`
  - Observable: Each subcommand locates its corresponding bundled script (`analyze-sessions.sh`, `create-summary-reports.sh`, `review-issues.sh`), forwards all arguments (including `--project-name`, `--project`, and extra `claude-args`), and propagates exit code. `i2code --help` lists the `improve` group.
  - Evidence: pytest tests using `CliRunner` with mocked `subprocess.run` verify correct script invocation for each subcommand; smoke test verifies all three appear in `i2code improve --help`
  - Steps:
    - [ ] Create `src/i2code/improve/__init__.py`
    - [ ] Create `src/i2code/improve/cli.py` with Click group `improve` (help text `"Analyze sessions, review issues, and update configuration."`) and commands `analyze_sessions_cmd` (script: `analyze-sessions.sh`), `summary_reports_cmd` (script: `create-summary-reports.sh`), `review_issues_cmd` (script: `review-issues.sh`)
    - [ ] Register `improve` group in `src/i2code/cli.py` via `main.add_command(improve)`
    - [ ] Create `tests/improve/__init__.py` and `tests/improve/conftest.py` (mark tests as `unit`)
    - [ ] Create `tests/improve/test_analyze_sessions_cli.py`, `tests/improve/test_summary_reports_cli.py`, `tests/improve/test_review_issues_cli.py` — verify each one incrementally
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check `i2code --help` contains `improve`, `i2code improve --help` contains all three subcommands, and verify `uv run i2code improve analyze-sessions --help`, `summary-reports --help`, and `review-issues --help` each exit 0

- [ ] **Task 3.2: `i2code improve update-claude-files` subcommand with config-dir modification**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve update-claude-files my-project-dir --config-dir /path/to/config-files`
  - Observable: `update-claude-files-from-project.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The `update-claude-files` subcommand invokes the modified script, forwarding all arguments including `--config-dir` and extra `claude-args`, and propagates exit code.
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies script is invoked with correct arguments
  - Steps:
    - [ ] Modify `src/i2code/scripts/update-claude-files-from-project.sh` to accept a `--config-dir` argument (parse it from the argument list) instead of using `$DIR/../config-files`. Also update the `git -C` reference to derive the git repo root from the config directory path.
    - [ ] Add `update_claude_files_cmd` to `src/i2code/improve/cli.py`
    - [ ] Create `tests/improve/test_update_claude_files_cli.py`
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `update-claude-files` in `improve --help`, and verify `uv run i2code improve update-claude-files --help` exits 0

---

- [ ] **Task 3.3: Remove migrated improve scripts from `workflow-scripts/`**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `workflow-scripts/analyze-sessions.sh`, `create-summary-reports.sh`, `review-issues.sh`, and `update-claude-files-from-project.sh` are removed from the repository. All tests continue to pass.
  - Evidence: `test-end-to-end.sh passes; listed scripts no longer exist in `workflow-scripts/``
  - Steps:
    - [ ] Run `git rm workflow-scripts/analyze-sessions.sh workflow-scripts/create-summary-reports.sh workflow-scripts/review-issues.sh workflow-scripts/update-claude-files-from-project.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Steel Thread 4: setup Subcommands with Config Directory Argument

Adds the `setup` group with two subcommands that accept `--config-dir` as a required argument, replacing the `$DIR/../config-files` path derivation.

- [ ] **Task 4.1: `i2code setup claude-files --config-dir <path>` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code setup claude-files --config-dir /path/to/config-files`
  - Observable: `setup-claude-files.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The `claude-files` subcommand invokes the modified script, forwarding `--config-dir` and any other arguments, and propagates exit code. `i2code --help` lists the `setup` group.
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies script is invoked with correct arguments
  - Steps:
    - [ ] Modify `src/i2code/scripts/setup-claude-files.sh` to accept a `--config-dir` argument instead of using `$DIR/../config-files`
    - [ ] Create `src/i2code/setup_cmd/__init__.py`
    - [ ] Create `src/i2code/setup_cmd/cli.py` with Click group `setup_group` (command name `"setup"`, help text `"Initial project setup and configuration updates."`) and `claude_files_cmd` (script: `setup-claude-files.sh`)
    - [ ] Register `setup_group` group in `src/i2code/cli.py` via `main.add_command(setup_group)`
    - [ ] Create `tests/setup-cmd/__init__.py` and `tests/setup-cmd/conftest.py` (mark tests as `unit`)
    - [ ] Create `tests/setup-cmd/test_claude_files_cli.py`
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check `i2code --help` contains `setup`, `i2code setup --help` contains `claude-files`, and verify `uv run i2code setup claude-files --help` exits 0

- [ ] **Task 4.2: `i2code setup update-project <project-dir> --config-dir <path>` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code setup update-project my-project-dir --config-dir /path/to/config-files`
  - Observable: `update-project-claude-files.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The git history lookup for config-files/ changes derives the repo root from the config-dir path. The `update-project` subcommand invokes the modified script, forwarding all arguments, and propagates exit code.
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies script is invoked with correct arguments
  - Steps:
    - [ ] Modify `src/i2code/scripts/update-project-claude-files.sh` to accept a `--config-dir` argument instead of using `$DIR/../config-files`. Update `git -C "$DIR/.."` to use `git -C "$(dirname "$CONFIG_DIR")"` for commit history lookup.
    - [ ] Add `update_project_cmd` to `src/i2code/setup_cmd/cli.py`
    - [ ] Create `tests/setup-cmd/test_update_project_cli.py`
    - [ ] Update `test-scripts/test-subcommands-smoke.sh` to check for `update-project` in `setup --help`, and verify `uv run i2code setup update-project --help` exits 0

---

- [ ] **Task 4.3: Remove migrated setup scripts from `workflow-scripts/`**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `workflow-scripts/setup-claude-files.sh` and `update-project-claude-files.sh` are removed from the repository. All tests continue to pass.
  - Evidence: `test-end-to-end.sh passes; listed scripts no longer exist in `workflow-scripts/``
  - Steps:
    - [ ] Run `git rm workflow-scripts/setup-claude-files.sh workflow-scripts/update-project-claude-files.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Steel Thread 5: Cleanup

Removes the original `workflow-scripts/` directory and dead code after all scripts have been migrated and verified.

- [ ] **Task 5.1: Remove remaining excluded files, `workflow-scripts/` directory, and update references**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: The remaining files in `workflow-scripts/` — `_helper.sh`, `_python_helper.sh`, `requirements.txt`, `implement-plan.sh`, `implement-with-worktree.sh`, `implement-todo-list.sh`, `refine-todo-list.sh` — are removed. The `workflow-scripts/` directory itself is deleted. All references to `workflow-scripts/` in the codebase (README, CLAUDE.md, docs, etc.) are updated or removed.
  - Evidence: `test-end-to-end.sh passes; `workflow-scripts/` directory no longer exists; `grep -r workflow-scripts` finds no stale references`
  - Steps:
    - [ ] Run `git rm` on remaining files: `workflow-scripts/_helper.sh`, `_python_helper.sh`, `requirements.txt`, `implement-plan.sh`, `implement-with-worktree.sh`, `implement-todo-list.sh`, `refine-todo-list.sh`
    - [ ] Remove the `workflow-scripts/` directory if not already empty
    - [ ] Search the codebase for remaining references to `workflow-scripts/` and update or remove them
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Summary

This plan has 5 steel threads and 10 tasks:
- **Thread 1** (3 tasks): Script runner infrastructure, first subcommand (`brainstorm`), CI smoke tests
- **Thread 2** (4 tasks): Remaining `idea-to-plan` subcommands including skill discovery helper
- **Thread 3** (2 tasks): `improve` subcommands including config-dir modification
- **Thread 4** (2 tasks): `setup` subcommands with config-dir modifications
- **Thread 5** (1 task): Remove `workflow-scripts/` directory

---

## Change History
### 2026-02-19 17:28 - insert-task-before
implement-plan.sh is excluded from scope (already replaced by i2code implement) and will not be present in the scripts bundle, so idea-to-code.sh must be updated to call i2code implement directly

### 2026-02-19 17:30 - insert-task-after
Remove old scripts incrementally as their subcommands are verified, rather than a big-bang cleanup at the end

### 2026-02-19 17:30 - insert-task-after
Remove old scripts incrementally as their subcommands are verified

### 2026-02-19 17:30 - insert-task-after
Remove old scripts incrementally as their subcommands are verified

### 2026-02-19 17:30 - insert-task-after
Remove old scripts incrementally as their subcommands are verified

### 2026-02-19 17:30 - replace-task
Slimmed down to only handle excluded/dead files and directory removal since migrated scripts are now removed incrementally in threads 1-4

### 2026-02-19 - updated smoke test steps
Added per-subcommand `--help` smoke tests: each task that adds subcommands now also verifies `uv run i2code <group> <subcommand> --help` exits 0. This catches broken imports or misconfigured command registration without executing shell scripts. Tests are added incrementally as each subcommand is wired up.
