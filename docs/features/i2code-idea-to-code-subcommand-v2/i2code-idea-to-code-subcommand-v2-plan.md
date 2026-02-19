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
  - Observable: run_script("brainstorm-idea.sh", ["my-dir"]) resolves the path to src/i2code/scripts/brainstorm-idea.sh, ensures execute permission, calls subprocess.run with [resolved_path, "my-dir"], and returns the subprocess result. Raises an error for scripts that do not exist in the bundle.
  - Evidence: `pytest tests pass with exit code 0`
  - Steps:
    - [x] git mv workflow-scripts/_helper.sh to src/i2code/scripts/_helper.sh and workflow-scripts/brainstorm-idea.sh to src/i2code/scripts/brainstorm-idea.sh (create src/i2code/scripts/ directory first)
    - [x] git mv prompt-templates/brainstorm-idea.md to src/i2code/prompt-templates/brainstorm-idea.md (create src/i2code/prompt-templates/ directory first)
    - [x] Update pyproject.toml [tool.hatch.build.targets.wheel] to include scripts/ and prompt-templates/ directories as package data
    - [x] Create src/i2code/script_runner.py with run_script(script_name, args=()) that: resolves path via Path(__file__).parent / "scripts" / script_name, raises FileNotFoundError if missing, ensures execute permission via os.chmod, calls subprocess.run([str(script_path)] + list(args)), and returns the CompletedProcess result
    - [x] Create tests/script-runner/__init__.py and tests/script-runner/conftest.py (mark tests as unit)
    - [x] Create tests/script-runner/test_script_runner.py with tests: resolves correct path, ensures executability, forwards arguments to subprocess, returns subprocess result, raises error for missing script
- [x] **Task 1.2: `i2code idea-to-plan brainstorm <dir>` invokes bundled brainstorm-idea.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan brainstorm my-dir`
  - Observable: The command locates `brainstorm-idea.sh` from bundled package data, invokes it via `subprocess.run` with `["my-dir"]` as arguments, and exits with the script's exit code
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies `brainstorm-idea.sh` is invoked with correct arguments and exit code is propagated
  - Steps:
    - [x] Create `src/i2code/idea_to_plan/__init__.py`
    - [x] Create `src/i2code/idea_to_plan/cli.py` with Click group `idea_to_plan` (command name `"idea-to-plan"`, help text `"Develop an idea into an implementation plan."`) and `brainstorm_cmd` that accepts `args` via `@click.argument("args", nargs=-1, type=click.UNPROCESSED)`, calls `run_script("brainstorm-idea.sh", args)`, and exits with the result's return code
    - [x] Register `idea_to_plan` group in `src/i2code/cli.py` via `main.add_command(idea_to_plan)`
    - [x] Create `tests/idea-to-plan/__init__.py` and `tests/idea-to-plan/conftest.py` (mark tests as `unit`)
    - [x] Create `tests/idea-to-plan/test_brainstorm_cli.py` that uses `CliRunner` and mocks `subprocess.run` to verify correct invocation

- [x] **Task 1.3: CLI smoke tests validate idea-to-plan group and brainstorm subcommand are discoverable**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code --help` lists `idea-to-plan` group; `i2code idea-to-plan --help` lists `brainstorm` subcommand with its help text
  - Evidence: `test-scripts/test-subcommands-smoke.sh` passes within `test-end-to-end.sh`; CI runs `test-end-to-end.sh` and passes
  - Steps:
    - [x] Create `test-scripts/test-subcommands-smoke.sh` that verifies `uv run i2code --help` contains `idea-to-plan`, `uv run i2code idea-to-plan --help` contains `brainstorm`, and `uv run i2code idea-to-plan brainstorm --help` exits 0 (follow the pattern in `test-scripts/test-plan-cli-smoke.sh`)
    - [x] Add `"$SCRIPT_DIR/test-subcommands-smoke.sh"` to `test-scripts/test-end-to-end.sh` after the plan CLI smoke tests line

---

## Steel Thread 2: Complete idea-to-plan Subcommands

Completes the `idea-to-plan` group with all remaining subcommands, including skill discovery modifications for `make-plan` and `design-doc`.

- [x] **Task 2.1: `i2code idea-to-plan spec` subcommand invokes bundled make-spec.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan spec my-dir`
  - Observable: The command locates make-spec.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments (including extra claude-args), and exits with the script's exit code
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies make-spec.sh is invoked with correct arguments and exit code is propagated`
  - Steps:
    - [x] git mv workflow-scripts/make-spec.sh to src/i2code/scripts/make-spec.sh
    - [x] git mv prompt-templates/create-spec.md to src/i2code/prompt-templates/create-spec.md
    - [x] Add spec_cmd to src/i2code/idea_to_plan/cli.py following the brainstorm pattern (script: make-spec.sh)
    - [x] Create tests/idea-to-plan/test_spec_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for spec in idea-to-plan --help and verify uv run i2code idea-to-plan spec --help exits 0
- [x] **Task 2.2: `i2code idea-to-plan revise-spec` subcommand invokes bundled revise-spec.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan revise-spec my-dir`
  - Observable: The command locates revise-spec.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments, and exits with the script's exit code
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies revise-spec.sh is invoked with correct arguments and exit code is propagated`
  - Steps:
    - [x] git mv workflow-scripts/revise-spec.sh to src/i2code/scripts/revise-spec.sh
    - [x] Add revise_spec_cmd to src/i2code/idea_to_plan/cli.py following the brainstorm pattern (script: revise-spec.sh)
    - [x] Create tests/idea-to-plan/test_revise_spec_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for revise-spec in idea-to-plan --help and verify uv run i2code idea-to-plan revise-spec --help exits 0
- [x] **Task 2.3: `i2code idea-to-plan revise-plan` subcommand invokes bundled revise-plan.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan revise-plan my-dir`
  - Observable: The command locates revise-plan.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments, and exits with the script's exit code
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies revise-plan.sh is invoked with correct arguments and exit code is propagated`
  - Steps:
    - [x] git mv workflow-scripts/revise-plan.sh to src/i2code/scripts/revise-plan.sh
    - [x] git mv prompt-templates/revise-plan.md to src/i2code/prompt-templates/revise-plan.md
    - [x] Add revise_plan_cmd to src/i2code/idea_to_plan/cli.py following the brainstorm pattern (script: revise-plan.sh)
    - [x] Create tests/idea-to-plan/test_revise_plan_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for revise-plan in idea-to-plan --help and verify uv run i2code idea-to-plan revise-plan --help exits 0
- [x] **Task 2.4: Skill discovery helper `list-plugin-skills.sh` and `i2code idea-to-plan make-plan` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan make-plan my-dir`
  - Observable: `list-plugin-skills.sh` searches `~/.claude/plugins/cache/` for the `idea-to-code` plugin, lists subdirectory names under its `skills/` directory, and outputs them as `idea-to-code:<skill-name>` comma-separated. If the plugin is not installed, it prints a warning to stderr and outputs an empty string. `make-plan.sh` (in `src/i2code/scripts/`) calls `list-plugin-skills.sh` instead of `ls -1 "/../skills"`. The `make-plan` subcommand invokes modified `make-plan.sh` and propagates exit code.
  - Evidence: `pytest test for make-plan subcommand verifies script invocation; shell test script validates list-plugin-skills.sh outputs correct format when plugin exists and outputs empty string with warning when plugin is absent`
  - Steps:
    - [x] git mv workflow-scripts/make-plan.sh to src/i2code/scripts/make-plan.sh
    - [x] git mv prompt-templates/create-implementation-plan.md to src/i2code/prompt-templates/create-implementation-plan.md
    - [x] Create src/i2code/scripts/list-plugin-skills.sh that: searches ~/.claude/plugins/cache/ for a directory matching *idea-to-code*/skills/, lists subdirectory names, formats as idea-to-code:<name> comma-separated, prints warning to stderr and outputs empty string if not found
    - [x] Modify src/i2code/scripts/make-plan.sh to replace ls -1 "$DIR/../skills" | sed ... with a call to $DIR/list-plugin-skills.sh
    - [x] Add make_plan_cmd to src/i2code/idea_to_plan/cli.py
    - [x] Create tests/idea-to-plan/test_make_plan_cli.py
    - [x] Create test-scripts/test-list-plugin-skills.sh that validates output format (add to test-end-to-end.sh)
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for make-plan in idea-to-plan --help, and verify uv run i2code idea-to-plan make-plan --help exits 0
- [x] **Task 2.5: `i2code idea-to-plan design-doc` subcommand with skill discovery**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan design-doc my-dir`
  - Observable: `create-design-doc.sh` (in `src/i2code/scripts/`) calls `list-plugin-skills.sh` instead of `ls -1 "/../skills"`. The `design-doc` subcommand invokes modified `create-design-doc.sh` and propagates exit code.
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies create-design-doc.sh is invoked with correct arguments`
  - Steps:
    - [x] git mv workflow-scripts/create-design-doc.sh to src/i2code/scripts/create-design-doc.sh
    - [x] git mv prompt-templates/create-design-doc.md to src/i2code/prompt-templates/create-design-doc.md
    - [x] Modify src/i2code/scripts/create-design-doc.sh to replace ls -1 "$DIR/../skills" | sed ... with a call to $DIR/list-plugin-skills.sh
    - [x] Add design_doc_cmd to src/i2code/idea_to_plan/cli.py
    - [x] Create tests/idea-to-plan/test_design_doc_cli.py
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for design-doc in idea-to-plan --help, and verify uv run i2code idea-to-plan design-doc --help exits 0
- [x] **Task 2.6: Modify `idea-to-code.sh` to call `i2code implement` instead of `implement-plan.sh`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan run my-dir`
  - Observable: `idea-to-code.sh` (in `src/i2code/scripts/`) replaces all references to `$SCRIPT_DIR/implement-plan.sh` with `i2code implement`. The orchestrator no longer depends on `implement-plan.sh` being present in the scripts bundle.
  - Evidence: `Manual review of modified idea-to-code.sh confirms no remaining references to implement-plan.sh; the run subcommand smoke test passes`
  - Steps:
    - [x] git mv workflow-scripts/idea-to-code.sh to src/i2code/scripts/idea-to-code.sh
    - [x] Modify src/i2code/scripts/idea-to-code.sh to replace "$SCRIPT_DIR/implement-plan.sh" "$dir" with i2code implement "$dir"
    - [x] Remove the "Implement a specific task" menu option since i2code implement does not support a task argument — renumber the Exit option accordingly
    - [x] Update the handle_error call for implement to reference i2code implement instead of $SCRIPT_DIR/implement-plan.sh
- [x] **Task 2.7: `i2code idea-to-plan run` subcommand invokes the orchestrator**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code idea-to-plan run my-dir`
  - Observable: The `run` subcommand invokes `idea-to-code.sh` with all forwarded arguments and propagates exit code
  - Evidence: pytest test using `CliRunner` with mocked `subprocess.run` verifies `idea-to-code.sh` is invoked with correct arguments
  - Steps:
    - [x] Add `run_cmd` to `src/i2code/idea_to_plan/cli.py` (script: `idea-to-code.sh`)
    - [x] Create `tests/idea-to-plan/test_run_cli.py`
    - [x] Update `test-scripts/test-subcommands-smoke.sh` to check for `run` in `idea-to-plan --help`, and verify `uv run i2code idea-to-plan run --help` exits 0

---

## Steel Thread 3: improve Subcommands

Adds the `improve` group with four subcommands for session analysis, summary reports, issue review, and Claude file updates.

- [x] **Task 3.1: `i2code improve analyze-sessions` subcommand and improve group infrastructure**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve analyze-sessions my-tracking-dir`
  - Observable: The command locates analyze-sessions.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments, and exits with the script's exit code. i2code --help lists the improve group.
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies analyze-sessions.sh is invoked with correct arguments and exit code is propagated; smoke test verifies improve group appears in i2code --help`
  - Steps:
    - [x] git mv workflow-scripts/analyze-sessions.sh to src/i2code/scripts/analyze-sessions.sh
    - [x] git mv prompt-templates/analyze-sessions.md to src/i2code/prompt-templates/analyze-sessions.md
    - [x] Create src/i2code/improve/__init__.py
    - [x] Create src/i2code/improve/cli.py with Click group improve (help text "Analyze sessions, review issues, and update configuration.") and analyze_sessions_cmd (script: analyze-sessions.sh)
    - [x] Register improve group in src/i2code/cli.py via main.add_command(improve)
    - [x] Create tests/improve/__init__.py and tests/improve/conftest.py (mark tests as unit)
    - [x] Create tests/improve/test_analyze_sessions_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check i2code --help contains improve, i2code improve --help contains analyze-sessions, and verify uv run i2code improve analyze-sessions --help exits 0
- [x] **Task 3.2: `i2code improve summary-reports` subcommand invokes bundled create-summary-reports.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve summary-reports my-hitl-dir`
  - Observable: The command locates create-summary-reports.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments (including --project-name), and exits with the script's exit code
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies create-summary-reports.sh is invoked with correct arguments and exit code is propagated`
  - Steps:
    - [x] git mv workflow-scripts/create-summary-reports.sh to src/i2code/scripts/create-summary-reports.sh
    - [x] git mv prompt-templates/create-summary-report.md to src/i2code/prompt-templates/create-summary-report.md
    - [x] Add summary_reports_cmd to src/i2code/improve/cli.py (script: create-summary-reports.sh)
    - [x] Create tests/improve/test_summary_reports_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for summary-reports in improve --help and verify uv run i2code improve summary-reports --help exits 0
- [x] **Task 3.3: `i2code improve review-issues` subcommand invokes bundled review-issues.sh**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve review-issues my-hitl-dir`
  - Observable: The command locates review-issues.sh from bundled package data, invokes it via subprocess.run with all forwarded arguments (including --project and extra claude-args), and exits with the script's exit code
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies review-issues.sh is invoked with correct arguments and exit code is propagated`
  - Steps:
    - [x] git mv workflow-scripts/review-issues.sh to src/i2code/scripts/review-issues.sh
    - [x] git mv prompt-templates/review-issues.md to src/i2code/prompt-templates/review-issues.md
    - [x] Add review_issues_cmd to src/i2code/improve/cli.py (script: review-issues.sh)
    - [x] Create tests/improve/test_review_issues_cli.py — verify with CliRunner and mocked subprocess.run
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for review-issues in improve --help and verify uv run i2code improve review-issues --help exits 0
- [x] **Task 3.4: `i2code improve update-claude-files` subcommand with config-dir modification**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code improve update-claude-files my-project-dir --config-dir /path/to/config-files`
  - Observable: `update-claude-files-from-project.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The `update-claude-files` subcommand invokes the modified script, forwarding all arguments including `--config-dir` and extra `claude-args`, and propagates exit code.
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies script is invoked with correct arguments`
  - Steps:
    - [x] git mv workflow-scripts/update-claude-files-from-project.sh to src/i2code/scripts/update-claude-files-from-project.sh
    - [x] git mv prompt-templates/update-claude-files-from-project.md to src/i2code/prompt-templates/update-claude-files-from-project.md
    - [x] Modify src/i2code/scripts/update-claude-files-from-project.sh to accept a --config-dir argument (parse it from the argument list) instead of using $DIR/../config-files. Also update the git repo root derivation to use the config directory path.
    - [x] Add update_claude_files_cmd to src/i2code/improve/cli.py
    - [x] Create tests/improve/test_update_claude_files_cli.py
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for update-claude-files in improve --help, and verify uv run i2code improve update-claude-files --help exits 0
## Steel Thread 4: setup Subcommands with Config Directory Argument

Adds the `setup` group with two subcommands that accept `--config-dir` as a required argument, replacing the `$DIR/../config-files` path derivation.

- [x] **Task 4.1: `i2code setup claude-files --config-dir <path>` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code setup claude-files --config-dir /path/to/config-files`
  - Observable: `setup-claude-files.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The `claude-files` subcommand invokes the modified script, forwarding `--config-dir` and any other arguments, and propagates exit code. `i2code --help` lists the `setup` group.
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies script is invoked with correct arguments`
  - Steps:
    - [x] git mv workflow-scripts/setup-claude-files.sh to src/i2code/scripts/setup-claude-files.sh
    - [x] Modify src/i2code/scripts/setup-claude-files.sh to accept a --config-dir argument instead of using $DIR/../config-files
    - [x] Create src/i2code/setup_cmd/__init__.py
    - [x] Create src/i2code/setup_cmd/cli.py with Click group setup_group (command name "setup", help text "Initial project setup and configuration updates.") and claude_files_cmd (script: setup-claude-files.sh)
    - [x] Register setup_group group in src/i2code/cli.py via main.add_command(setup_group)
    - [x] Create tests/setup-cmd/__init__.py and tests/setup-cmd/conftest.py (mark tests as unit)
    - [x] Create tests/setup-cmd/test_claude_files_cli.py
    - [x] Update test-scripts/test-subcommands-smoke.sh to check i2code --help contains setup, i2code setup --help contains claude-files, and verify uv run i2code setup claude-files --help exits 0
- [x] **Task 4.2: `i2code setup update-project <project-dir> --config-dir <path>` subcommand**
  - TaskType: OUTCOME
  - Entrypoint: `uv run i2code setup update-project my-project-dir --config-dir /path/to/config-files`
  - Observable: `update-project-claude-files.sh` (in `src/i2code/scripts/`) accepts config directory as a new argument instead of deriving it from `$DIR/../config-files`. The git history lookup for config-files/ changes derives the repo root from the config-dir path. The `update-project` subcommand invokes the modified script, forwarding all arguments, and propagates exit code.
  - Evidence: `pytest test using CliRunner with mocked subprocess.run verifies script is invoked with correct arguments`
  - Steps:
    - [x] git mv workflow-scripts/update-project-claude-files.sh to src/i2code/scripts/update-project-claude-files.sh
    - [x] git mv prompt-templates/update-project-claude-files.md to src/i2code/prompt-templates/update-project-claude-files.md
    - [x] Modify src/i2code/scripts/update-project-claude-files.sh to accept a --config-dir argument instead of using $DIR/../config-files. Update git repo root derivation to use the config-dir path for commit history lookup.
    - [x] Add update_project_cmd to src/i2code/setup_cmd/cli.py
    - [x] Create tests/setup-cmd/test_update_project_cli.py
    - [x] Update test-scripts/test-subcommands-smoke.sh to check for update-project in setup --help, and verify uv run i2code setup update-project --help exits 0
## Steel Thread 5: Cleanup

Removes the original `workflow-scripts/` directory and dead code after all scripts have been migrated and verified.

- [x] **Task 5.1: Remove remaining excluded files, `workflow-scripts/` directory, and update references**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: The remaining files in `workflow-scripts/` — `_helper.sh`, `_python_helper.sh`, `requirements.txt`, `implement-plan.sh`, `implement-with-worktree.sh`, `implement-todo-list.sh`, `refine-todo-list.sh` — are removed. The `workflow-scripts/` directory itself is deleted. All references to `workflow-scripts/` in the codebase (README, CLAUDE.md, docs, etc.) are updated or removed.
  - Evidence: `test-end-to-end.sh passes; `workflow-scripts/` directory no longer exists; `grep -r workflow-scripts` finds no stale references`
  - Steps:
    - [x] Run `git rm` on remaining files: `workflow-scripts/_helper.sh`, `_python_helper.sh`, `requirements.txt`, `implement-plan.sh`, `implement-with-worktree.sh`, `implement-todo-list.sh`, `refine-todo-list.sh`
    - [x] Remove the `workflow-scripts/` directory if not already empty
    - [x] Search the codebase for remaining references to `workflow-scripts/` and update or remove them
    - [x] Run `./test-scripts/test-end-to-end.sh` to confirm everything still passes
## Steel Thread 6: Extract Script Command Factory to Eliminate Boilerplate

Replaces the repeated Click decorator + `run_script` + `sys.exit` pattern with a `script_command()` factory function. Each subcommand becomes a single function call. Tests are parametrized accordingly.

- [x] **Task 6.1: Extract `script_command()` factory and convert `improve` group**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/improve/ tests/script-runner/ -v -m unit`
  - Observable: A new `script_command(group, name, script_name, help_text)` function in `src/i2code/script_command.py` generates Click commands that accept unprocessed args, call `run_script`, and `sys.exit`. `improve/cli.py` uses `script_command()` for all four subcommands — no per-command function definitions remain. All existing tests still pass unchanged.
  - Evidence: `pytest tests pass with exit code 0; smoke tests pass`
  - Steps:
    - [x] Create `src/i2code/script_command.py` with `script_command(group, name, script_name, help_text)` that registers a Click command on `group` using `context_settings={"ignore_unknown_options": True}`, `@click.argument("args", nargs=-1, type=click.UNPROCESSED)`, calls `run_script(script_name, args)`, and `sys.exit(result.returncode)`
    - [x] Create `tests/script-runner/test_script_command.py` with tests verifying: command is registered on group, help text is set, args are forwarded to `run_script`, exit code is propagated
    - [x] Rewrite `src/i2code/improve/cli.py` to use `script_command()` — replace the four decorated function definitions with four `script_command()` calls
    - [x] Run all improve tests and smoke tests to confirm no regressions

- [ ] **Task 6.2: Convert `setup` and `idea-to-plan` groups to use `script_command()`**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ tests/idea-to-plan/ -v -m unit`
  - Observable: `setup_cmd/cli.py` and `idea_to_plan/cli.py` use `script_command()` for all subcommands — no per-command function definitions remain. All existing tests still pass unchanged.
  - Evidence: `pytest tests pass with exit code 0; smoke tests pass`
  - Steps:
    - [ ] Rewrite `src/i2code/setup_cmd/cli.py` to use `script_command()` — replace the two decorated function definitions with two `script_command()` calls
    - [ ] Rewrite `src/i2code/idea_to_plan/cli.py` to use `script_command()` — replace the seven decorated function definitions with seven `script_command()` calls
    - [ ] Run all setup-cmd, idea-to-plan tests and smoke tests to confirm no regressions

- [ ] **Task 6.3: Parametrize duplicate test classes into a single shared test**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/script-command/ -v -m unit`
  - Observable: A single parametrized test class in `tests/script-command/test_all_script_commands.py` covers all 13 script commands. Each entry specifies (cli_args, expected_script_name, expected_forwarded_args). Variant argument patterns (extra flags, `--` separator) are additional entries in the parametrized list. Help-output tests are dropped (already covered by smoke tests). The 13 per-subcommand test files are removed. Test count is equal or greater than before.
  - Evidence: `pytest tests pass with exit code 0; test count is equal or greater than before`
  - Steps:
    - [ ] Create `tests/script-command/__init__.py` and `tests/script-command/conftest.py`
    - [ ] Create `tests/script-command/test_all_script_commands.py` with `SCRIPT_COMMANDS` list of (cli_args, script_name, expected_args) tuples — include multiple entries per subcommand where variant arg patterns exist (e.g., extra flags, `--` separator forwarding). Parametrize `TestScriptCommand` class with `test_invokes_correct_script_with_args` and `test_propagates_script_exit_code`.
    - [ ] Remove the 13 per-subcommand test files now covered by the parametrized test
    - [ ] Run full test suite and smoke tests to confirm no regressions

---

## Summary

This plan has 6 steel threads and 20 tasks:
- **Thread 1** (3 tasks): Script runner infrastructure, first subcommand (`brainstorm`), CI smoke tests
- **Thread 2** (7 tasks): Remaining `idea-to-plan` subcommands including skill discovery helper
- **Thread 3** (4 tasks): `improve` subcommands including config-dir modification
- **Thread 4** (2 tasks): `setup` subcommands with config-dir modifications
- **Thread 5** (1 task): Remove remaining excluded files and `workflow-scripts/` directory
- **Thread 6** (3 tasks): Extract `script_command()` factory, convert all groups, parametrize tests

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

### 2026-02-19 18:13 - delete-task
git mv handles removal; no separate cleanup task needed

### 2026-02-19 18:13 - delete-task
git mv handles removal; no separate cleanup task needed

### 2026-02-19 18:13 - delete-task
git mv handles removal; no separate cleanup task needed

### 2026-02-19 18:13 - delete-task
git mv handles removal; no separate cleanup task needed

### 2026-02-19 18:14 - replace-task
Replace bulk copy of all 14 scripts with incremental git mv of only the files needed for this task

### 2026-02-19 18:14 - replace-task
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:14 - insert-task-after
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:14 - insert-task-after
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:14 - replace-task
Add incremental git mv of make-plan.sh and create-implementation-plan.md

### 2026-02-19 18:14 - replace-task
Add incremental git mv of create-design-doc.sh and create-design-doc.md

### 2026-02-19 18:15 - replace-task
Add incremental git mv of idea-to-code.sh

### 2026-02-19 18:15 - replace-task
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:15 - insert-task-after
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:15 - insert-task-after
Split bundled 3-subcommand task into individual tasks for incremental development

### 2026-02-19 18:16 - replace-task
Add incremental git mv of update-claude-files-from-project.sh and its prompt template

### 2026-02-19 18:16 - replace-task
Add incremental git mv of setup-claude-files.sh

### 2026-02-19 18:16 - replace-task
Add incremental git mv of update-project-claude-files.sh and its prompt template

### 2026-02-19 - plan revision: incremental development and git mv
Three structural revisions applied to enforce incremental-development and file-organization skills:
1. **Split bundled tasks** — Tasks 2.1 (spec + revise-spec + revise-plan) and 3.1 (analyze-sessions + summary-reports + review-issues) each split into one task per subcommand (10→17 tasks total)
2. **Incremental git mv** — Each task now `git mv`s only the scripts and prompt templates it needs, replacing the bulk copy of all 14 scripts and 10 templates in Task 1.1
3. **Eliminated cleanup tasks** — Deleted Tasks 1.4, 2.6, 3.3, 4.3 (separate "remove migrated scripts" steps) since `git mv` handles the move and removal atomically

### 2026-02-19 18:53 - mark-step-complete
git mv _helper.sh and brainstorm-idea.sh to src/i2code/scripts/

### 2026-02-19 18:53 - mark-step-complete
git mv brainstorm-idea.md to src/i2code/prompt-templates/

### 2026-02-19 18:54 - mark-step-complete
pyproject.toml packages=['src/i2code'] already includes all files under src/i2code/ - no change needed, consistent with existing .j2 templates

### 2026-02-19 18:55 - mark-step-complete
Created src/i2code/script_runner.py with run_script function

### 2026-02-19 18:55 - mark-step-complete
Created tests/script-runner/__init__.py and conftest.py with unit marker

### 2026-02-19 18:55 - mark-step-complete
Created test_script_runner.py with 5 tests: resolves path, ensures executability, forwards args, returns result, raises for missing

### 2026-02-19 18:55 - mark-task-complete
All 5 tests pass: resolves path, ensures executability, forwards args, returns result, raises for missing script

### 2026-02-19 19:06 - mark-step-complete
Created test-subcommands-smoke.sh with 3 checks: idea-to-plan in i2code --help, brainstorm in idea-to-plan --help, brainstorm --help exits 0

### 2026-02-19 19:06 - mark-step-complete
Added test-subcommands-smoke.sh to test-end-to-end.sh after plan CLI smoke tests

### 2026-02-19 19:06 - mark-task-complete
All 3 smoke tests pass: idea-to-plan in i2code --help, brainstorm in idea-to-plan --help, brainstorm --help exits 0. Integrated into test-end-to-end.sh.

### 2026-02-19 19:10 - mark-step-complete
git mv workflow-scripts/make-spec.sh to src/i2code/scripts/make-spec.sh

### 2026-02-19 19:10 - mark-step-complete
git mv prompt-templates/create-spec.md to src/i2code/prompt-templates/create-spec.md

### 2026-02-19 19:10 - mark-step-complete
Added spec_cmd to cli.py following brainstorm pattern

### 2026-02-19 19:10 - mark-step-complete
Created test_spec_cli.py with CliRunner and mocked subprocess.run

### 2026-02-19 19:10 - mark-step-complete
Updated smoke tests for spec in idea-to-plan --help and --help exits 0

### 2026-02-19 19:11 - mark-task-complete
spec subcommand invokes bundled make-spec.sh with tests passing

### 2026-02-19 19:15 - mark-step-complete
git mv workflow-scripts/revise-spec.sh src/i2code/scripts/revise-spec.sh

### 2026-02-19 19:15 - mark-step-complete
Added revise_spec_cmd to cli.py following brainstorm/spec pattern

### 2026-02-19 19:15 - mark-step-complete
Created test_revise_spec_cli.py with CliRunner and mocked subprocess.run

### 2026-02-19 19:16 - mark-step-complete
Updated smoke test to check revise-spec in idea-to-plan --help and --help exits 0

### 2026-02-19 19:16 - mark-task-complete
revise-spec subcommand invokes bundled revise-spec.sh, verified by pytest and smoke tests

### 2026-02-19 19:30 - mark-step-complete
git mv workflow-scripts/make-plan.sh src/i2code/scripts/make-plan.sh

### 2026-02-19 19:31 - mark-step-complete
git mv prompt-templates/create-implementation-plan.md src/i2code/prompt-templates/

### 2026-02-19 19:31 - mark-step-complete
Created list-plugin-skills.sh with PLUGIN_CACHE_DIR override for testing

### 2026-02-19 19:31 - mark-step-complete
Replaced ls -1 skills pipe with call to list-plugin-skills.sh

### 2026-02-19 19:31 - mark-step-complete
Added make_plan_cmd to cli.py following established pattern

### 2026-02-19 19:31 - mark-step-complete
Created test_make_plan_cli.py with invocation and exit code tests

### 2026-02-19 19:31 - mark-step-complete
Created test-list-plugin-skills.sh validating plugin-exists, plugin-absent, and single-skill scenarios; added to test-end-to-end.sh

### 2026-02-19 19:31 - mark-step-complete
Added make-plan checks to test-subcommands-smoke.sh

### 2026-02-19 19:31 - mark-task-complete
All 8 steps complete: git-moved make-plan.sh and prompt template, created list-plugin-skills.sh, modified make-plan.sh to use it, added CLI command, pytest tests, shell tests, and smoke tests

### 2026-02-19 19:37 - mark-task-complete
Implemented design-doc subcommand with plugin skill discovery

### 2026-02-19 19:42 - mark-task-complete
Moved idea-to-code.sh to src/i2code/scripts/, replaced implement-plan.sh with i2code implement, removed specific task menu option

### 2026-02-19 19:47 - mark-task-complete
Added run_cmd to cli.py, created test_run_cli.py, updated smoke tests

### 2026-02-19 19:53 - mark-task-complete
Implemented improve group with analyze-sessions subcommand, tests pass

### 2026-02-19 19:58 - mark-step-complete
git mv workflow-scripts/create-summary-reports.sh to src/i2code/scripts/

### 2026-02-19 19:58 - mark-step-complete
git mv prompt-templates/create-summary-report.md to src/i2code/prompt-templates/

### 2026-02-19 19:58 - mark-step-complete
Added summary_reports_cmd to src/i2code/improve/cli.py

### 2026-02-19 19:58 - mark-step-complete
Created tests/improve/test_summary_reports_cli.py with 4 tests, all pass

### 2026-02-19 19:58 - mark-step-complete
Updated test-scripts/test-subcommands-smoke.sh with summary-reports checks

### 2026-02-19 19:58 - mark-task-complete
summary-reports subcommand implemented with bundled script, tests pass

### 2026-02-19 20:03 - mark-task-complete
review-issues subcommand implemented with bundled script, tests, and smoke tests

### 2026-02-19 20:10 - mark-task-complete
Implemented update-claude-files subcommand: moved script and prompt template to bundled locations, modified script to accept --config-dir argument, added CLI command, created pytest tests, updated smoke tests

### 2026-02-19 20:17 - mark-step-complete
git mv workflow-scripts/setup-claude-files.sh to src/i2code/scripts/setup-claude-files.sh

### 2026-02-19 20:17 - mark-step-complete
Modified setup-claude-files.sh to accept --config-dir argument with usage/help and validation

### 2026-02-19 20:17 - mark-step-complete
Created src/i2code/setup_cmd/__init__.py

### 2026-02-19 20:17 - mark-step-complete
Created setup_cmd/cli.py with setup_group and claude_files_cmd

### 2026-02-19 20:17 - mark-step-complete
Registered setup_group in src/i2code/cli.py via main.add_command(setup_group)

### 2026-02-19 20:17 - mark-step-complete
Created tests/setup-cmd/__init__.py and conftest.py with unit marker

### 2026-02-19 20:17 - mark-step-complete
Created test_claude_files_cli.py with 5 tests verifying script invocation, exit code propagation, arg forwarding, and help output

### 2026-02-19 20:17 - mark-step-complete
Updated smoke tests to check i2code --help contains setup, setup --help contains claude-files, and claude-files --help exits 0

### 2026-02-19 20:17 - mark-task-complete
Implemented setup group with claude-files subcommand: moved and modified setup-claude-files.sh to accept --config-dir, created setup_cmd package, pytest tests (5 pass), smoke tests pass

### 2026-02-19 20:21 - mark-step-complete
git mv workflow-scripts/update-project-claude-files.sh to src/i2code/scripts/

### 2026-02-19 20:21 - mark-step-complete
git mv prompt-templates/update-project-claude-files.md to src/i2code/prompt-templates/

### 2026-02-19 20:23 - mark-step-complete
Added update_project_cmd to setup_cmd/cli.py

### 2026-02-19 20:23 - mark-step-complete
Created test_update_project_cli.py with 4 tests, all pass

### 2026-02-19 20:23 - mark-step-complete
Modified script to accept --config-dir argument with argument parsing, git repo root derivation from config-dir path

### 2026-02-19 20:24 - mark-step-complete
Updated smoke tests to check update-project in setup --help and --help exits 0

### 2026-02-19 20:25 - mark-task-complete
Implemented update-project subcommand: moved script and prompt template, modified script to accept --config-dir with git repo root derivation, added CLI command, pytest tests (4 pass), smoke tests pass

### 2026-02-19 20:33 - mark-task-complete
Removed all workflow-scripts/ files, directory, and updated stale references in README.adoc, docs/scripts/, docs/idea-to-code-workflow.adoc. Deleted obsolete test files for removed scripts.

### 2026-02-20 07:34 - mark-task-complete
Extracted script_command() factory, added tests, converted improve/cli.py — all 26 tests pass
