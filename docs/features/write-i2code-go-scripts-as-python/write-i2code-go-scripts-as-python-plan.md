Now I have comprehensive understanding of the codebase. Let me generate the plan.

---

# Migrate i2code Bash Scripts to Python — Implementation Plan

## Idea Type

C — Platform/Infrastructure Capability

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
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |

### TDD Requirements

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be `./test-scripts/test-end-to-end.sh` or `uv run --python 3.12 python3 -m pytest tests/ -v -m unit`), its exit code, and the last 20 lines of output

## Overview

Incrementally migrate all `i2code` bash scripts to Python, following the command/assembler/strategy patterns established by the `implement` command. Each workflow step becomes a standalone, tested Python function/class. The migration preserves all user-facing behavior (CLI commands, arguments, menus, output, exit codes).

All tasks should be implemented using TDD.

### Current Architecture

- **CLI entry point:** `src/i2code/cli.py` — Click group registering subcommands
- **Bash delegation:** `src/i2code/script_command.py` + `src/i2code/script_runner.py` wrap 14 bash scripts as Click commands
- **Bash scripts:** `src/i2code/scripts/` (15 files including `_helper.sh`)
- **Existing Python commands:** `implement`, `scaffold`, `plan`, `tracking` — follow assembler/strategy patterns with `IdeaProject`, `ClaudeRunner`
- **Tests:** pytest in `tests/` (unit/integration markers) + bash test scripts in `test-scripts/`
- **CI:** `.github/workflows/ci.yml` runs `./test-scripts/test-end-to-end.sh` which calls both pytest and bash test scripts

### Migration Pattern (repeated for each script)

1. Create Python module implementing the script's behavior
2. Write pytest tests covering the behavior (replaces bash tests)
3. Update the subgroup's `cli.py` to register a direct Click command (replacing `script_command()`)
4. Update the Python orchestrator to call the Python function (replacing `script_runner` delegation)
5. Delete the bash script
6. Remove corresponding bash test script from `test-scripts/test-end-to-end.sh`

### Key Design Decisions

- `input()` menus (no new dependencies)
- `string.Template` for prompt templates (compatible with existing `$VARIABLE` syntax in `src/i2code/prompt-templates/`)
- Extend `IdeaProject` for path derivation and validation (replaces `_helper.sh`)
- Reuse `ClaudeRunner` for Claude invocation via subprocess
- Dependencies injectable via constructors for testability (following `command_assembler.py` pattern)

---

## Steel Thread 1: Workflow Orchestrator

Replace `idea-to-code.sh` (the largest and highest-risk script at ~490 lines) with a Python state machine. During this transition, the Python orchestrator delegates to remaining bash scripts via `script_runner.py`.

- [x] **Task 1.1: Orchestrator detects workflow state and presents correct menu**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit`
  - Observable: Given an idea project directory at each workflow state (`no_idea`, `has_idea_no_spec`, `has_spec`, `has_plan`), the orchestrator identifies the state based on file existence and presents the corresponding numbered menu with correct options
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit` passes with assertions for all four states and their menu options
  - Steps:
    - [x] Extend `IdeaProject` in `src/i2code/implement/idea_project.py` with derived path properties: `idea_file` (supports `.md` or `.txt` with glob), `spec_file`, `discussion_file`, `design_file`, `story_file`, `plan_with_stories_file`, `session_id_file`, `implement_config_file`. Follow the naming from `src/i2code/scripts/_helper.sh:1-35`
    - [x] Add validation methods to `IdeaProject`: `validate_idea()`, `validate_spec()`, `validate_plan()` that print to stderr and raise `SystemExit(1)` if the file is missing — matching `_helper.sh:38-79`
    - [x] Create `src/i2code/go_cmd/__init__.py`
    - [x] Create `src/i2code/go_cmd/menu.py` — reusable `get_user_choice(prompt, default, options, *, input_fn=input, output=sys.stderr)` that displays numbered options to stderr, validates input, handles EOF, returns the selected option index. Match behavior of `idea-to-code.sh:45-89`
    - [x] Create `src/i2code/go_cmd/orchestrator.py` — `Orchestrator` class with constructor-injected dependencies (`IdeaProject`, menu presenter, step dispatcher). `detect_state()` method checks file existence via `IdeaProject` properties and returns state enum. `run()` method implements the main loop: detect state → present menu → dispatch → repeat
    - [x] Create `tests/go-cmd/` directory with pytest tests covering: state detection for all four states, correct menu options per state, invalid input handling, EOF handling

- [x] **Task 1.2: Orchestrator dispatches workflow steps and handles errors**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit`
  - Observable: When a user selects a menu option, the orchestrator invokes the corresponding bash script via `script_runner` and loops back. On step failure, presents Retry/Abort menu. On Ctrl+C, exits with code 130. When git has uncommitted changes in the idea directory, adds "Commit changes" to the `has_plan` menu.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit` passes with mocked `script_runner` and mocked `subprocess` for git
  - Steps:
    - [x] Add step dispatch to the orchestrator: map each menu selection to its `run_script()` call — brainstorm → `brainstorm-idea.sh`, create spec → `make-spec.sh`, revise spec → `revise-spec.sh`, create plan → `make-plan.sh`, revise plan → `revise-plan.sh`. Match `idea-to-code.sh:261-338`
    - [x] Implement `run_step(description, callback)` that prints description and calls the callback, matching `idea-to-code.sh:24-42`
    - [x] Implement error handling: on non-zero exit code, present Retry/Abort menu via `get_user_choice`. Retry re-runs the step; Abort exits with code 1. Match `idea-to-code.sh:108-123`
    - [x] Implement `KeyboardInterrupt` handler that prints "Workflow interrupted." and calls `sys.exit(130)`. Match `idea-to-code.sh:126`
    - [x] Implement git dirty detection: call `git status --porcelain -- <dir>` via `subprocess`. When dirty, insert "Commit changes" option in `has_plan` menu. Commit action runs `git add <dir>` then `git commit -m "Add idea docs for <name>"`. Match `idea-to-code.sh:92-105`
    - [x] Write pytest tests for: dispatch invokes correct script, retry/abort flow, KeyboardInterrupt exit code, git dirty adds commit option, commit action stages and commits

- [x] **Task 1.3: Orchestrator manages implement configuration**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit`
  - Observable: Orchestrator reads and writes `{name}-implement-config.yaml` containing `interactive` and `trunk` boolean flags. Prompts on first implement run; reuses config on subsequent runs. "Configure implement options" menu item available after config exists. Implement menu label shows `i2code implement` with correct flags.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit` passes with assertions on config file creation, re-reading, flag construction, and menu label
  - Steps:
    - [x] Create `src/i2code/go_cmd/implement_config.py` with functions: `read_implement_config(path) -> dict`, `write_implement_config(path, interactive, trunk)`, `prompt_implement_config(menu_fn) -> (interactive, trunk)`, `build_implement_flags(config) -> list[str]`, `build_implement_label(config_path) -> str`. Match `idea-to-code.sh:129-199`
    - [x] Integrate into orchestrator's `has_plan` state: on "Implement" selection, check for config file → prompt if missing → display config → invoke `i2code implement` with flags. "Configure implement options" re-prompts and overwrites config. Match `idea-to-code.sh:340-468`
    - [x] Implement plan completion check: after successful implement, check for remaining `[ ]` in plan file. If all complete, print "Workflow Complete!" and exit 0. Match `idea-to-code.sh:387-398`
    - [x] Write pytest tests for: config write/read round-trip, prompt flow with mocked menu, flag construction (`--non-interactive`, `--trunk`), label formatting, plan completion detection

- [x] **Task 1.4: Wire orchestrator as Click command, delete bash script and tests**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code go <directory>` invokes the Python orchestrator. Directory creation prompt works for non-existent directories. Banner displays project name and directory. The bash script `idea-to-code.sh` is deleted. Bash test scripts for `i2code go` are replaced by pytest tests. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes (includes both pytest unit tests and remaining bash tests)
  - Steps:
    - [x] Create `src/i2code/go_cmd/cli.py` with Click command `go_cmd` that: takes `directory` argument, handles non-existent directory with create prompt (matching `idea-to-code.sh:215-233`), constructs `IdeaProject`, assembles `Orchestrator` with all dependencies, calls `orchestrator.run()`. Follow `command_assembler.py` pattern for dependency wiring.
    - [x] In `src/i2code/cli.py`: remove `script_command(main, "go", ...)` on line 47, add `from i2code.go_cmd.cli import go_cmd` and `main.add_command(go_cmd)`
    - [x] Write CLI integration test using Click's `CliRunner` verifying the command is registered and invokes the orchestrator
    - [x] Delete `src/i2code/scripts/idea-to-code.sh`
    - [x] Remove `test-scripts/test-i2code-go.sh` invocation from `test-scripts/test-end-to-end.sh`. Delete `test-scripts/test-i2code-go.sh`, `test-scripts/test-go-commit-menu.sh`, `test-scripts/test-go-commit-action.sh`, `test-scripts/test-go-commit-failure.sh`, `test-scripts/test-go-skip-commit.sh`, `test-scripts/test-implement-config.sh`
    - [x] Run `./test-scripts/test-end-to-end.sh` to verify CI-equivalent passes

---

## Steel Thread 2: Specification Workflow

Migrate `make-spec.sh` and `revise-spec.sh` to Python. Introduces the template renderer and session manager as shared infrastructure.

- [x] **Task 2.1: `i2code spec create` generates specification via Claude**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit`
  - Observable: Given an idea project with an idea file, loads `create-spec.md` from `src/i2code/prompt-templates/`, substitutes `$IDEA_FILE` and `$DISCUSSION_FILE` using `string.Template`, reads session ID if present (resumes session) or starts new session, and invokes Claude interactively with the rendered prompt
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit` passes with mocked ClaudeRunner verifying template rendering, session flag construction, and Claude invocation with correct arguments
  - Steps:
    - [x] Create `src/i2code/template_renderer.py` — `render_template(template_name, variables) -> str` that loads a file from `src/i2code/prompt-templates/<template_name>` and substitutes `$VARIABLE` placeholders using `string.Template`. Uses `importlib.resources` or `Path(__file__).parent` to locate the templates directory.
    - [x] Create `src/i2code/session_manager.py` — `read_session_id(path) -> Optional[str]` that reads session ID from file if it exists. `build_session_args(session_id_path) -> list[str]` that returns `["--resume", id]` if session file exists, else empty list.
    - [x] Create `src/i2code/spec_cmd/create_spec.py` — `create_spec(project: IdeaProject, claude_runner, template_renderer, session_manager)` function that: validates idea via `project.validate_idea()`, renders `create-spec.md` with `IDEA_FILE` and `DISCUSSION_FILE`, builds session args, invokes Claude interactively via `claude_runner.run_interactive()`. Match `scripts/make-spec.sh`
    - [x] Write pytest tests in `tests/spec-cmd/` with mocked ClaudeRunner: idea validation, template rendered with correct variables, session resume when session file exists, new session when no session file, Claude invoked with correct command

- [x] **Task 2.2: `i2code spec revise` revises specification via Claude**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit`
  - Observable: Validates idea and spec files exist, constructs inline revision prompt referencing the three files (idea, discussion, spec), and invokes Claude interactively
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit` passes with mocked ClaudeRunner
  - Steps:
    - [x] Create `src/i2code/spec_cmd/revise_spec.py` — `revise_spec(project: IdeaProject, claude_runner)` function that: validates idea and spec exist, constructs inline prompt matching `scripts/revise-spec.sh:11-17` (lists idea, discussion, and spec file paths), invokes Claude interactively
    - [x] Write pytest tests: validates both files, prompt contains all three file paths, Claude invoked

- [x] **Task 2.3: Wire spec commands, update orchestrator, delete bash scripts**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code spec create <dir>` and `i2code spec revise <dir>` invoke Python implementations. Orchestrator calls Python functions instead of `script_runner`. Bash scripts `make-spec.sh` and `revise-spec.sh` are deleted. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes
  - Steps:
    - [x] Update `src/i2code/spec_cmd/cli.py`: remove `script_command` imports and calls, create direct Click commands for `create` and `revise` that take `directory` argument, construct `IdeaProject`, and call the Python functions with injected dependencies
    - [x] Update `src/i2code/go_cmd/orchestrator.py`: replace `run_script("make-spec.sh", ...)` and `run_script("revise-spec.sh", ...)` calls with direct Python function calls to `create_spec()` and `revise_spec()`
    - [x] Write CLI integration tests using CliRunner for both `i2code spec create` and `i2code spec revise`
    - [x] Delete `src/i2code/scripts/make-spec.sh` and `src/i2code/scripts/revise-spec.sh`
    - [x] Run `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 3: Idea Brainstorming

Migrate `brainstorm-idea.sh` to Python. Handles directory creation, editor detection, session management with UUID generation, and Claude invocation.

- [x] **Task 3.1: `i2code idea brainstorm` launches editor and invokes Claude**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/idea-cmd/ -v -m unit`
  - Observable: Creates idea directory if missing. Detects editor in order: `code --wait` → `$VISUAL` → `$EDITOR` → `vi`. Creates idea file with "PLEASE DESCRIBE YOUR IDEA" template and opens in editor. Generates UUID session ID for new sessions (writes to session ID file), resumes existing sessions. Invokes Claude with `brainstorm-idea.md` template.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/idea-cmd/ -v -m unit` passes with mocked subprocess verifying editor launch order, session ID generation, and Claude invocation
  - Steps:
    - [x] Extend `src/i2code/session_manager.py` with `create_session_id(path) -> str` that generates a UUID via `uuid.uuid4()`, writes it to the session ID file, and returns it. Add `get_or_create_session_args(session_id_path) -> list[str]` that returns `["--resume", id]` for existing sessions or `["--session-id", new_id]` for new ones.
    - [x] Create `src/i2code/idea_cmd/brainstorm.py` — `brainstorm_idea(project: IdeaProject, claude_runner, template_renderer, session_manager, *, run_editor)` function that: creates directory if needed, detects editor (`code`, `$VISUAL`, `$EDITOR`, `vi`), creates idea file with template text, launches editor via `run_editor` callback, renders `brainstorm-idea.md` template, builds session args, invokes Claude. Match `scripts/brainstorm-idea.sh`
    - [x] Write pytest tests: directory creation when missing, editor detection order (mock `shutil.which` for `code`, mock env vars for `VISUAL`/`EDITOR`), idea file creation with template, session ID generation for new session, session resume for existing, Claude invoked with correct prompt and session args

- [x] **Task 3.2: Wire brainstorm command, update orchestrator, delete bash script**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code idea brainstorm <dir>` invokes Python implementation. Orchestrator calls Python function. Bash script `brainstorm-idea.sh` deleted. Editor resolution bash test replaced by pytest. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes
  - Steps:
    - [x] Update `src/i2code/idea_cmd/cli.py`: remove `script_command` calls, create direct Click command for `brainstorm` that constructs `IdeaProject` and calls `brainstorm_idea()` with injected dependencies
    - [x] Update orchestrator: replace `run_script("brainstorm-idea.sh", ...)` with direct call to `brainstorm_idea()`
    - [x] Write CLI integration test using CliRunner
    - [x] Delete `src/i2code/scripts/brainstorm-idea.sh`
    - [x] Remove `test-scripts/test-editor-resolution.sh` from `test-scripts/test-end-to-end.sh` and delete it (editor detection now covered by pytest)
    - [x] Run `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 4: Plan Workflow

Migrate `make-plan.sh`, `revise-plan.sh`, and `list-plugin-skills.sh`. Includes the plan validator (rewriting AWK as Python) and auto-repair logic.

- [x] **Task 4.1: Plugin skill enumeration lists installed skills**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k plugin_skills`
  - Observable: Searches `$PLUGIN_CACHE_DIR` (default `~/.claude/plugins/cache`) for `idea-to-code` plugin. Lists subdirectory names under the plugin's `skills/` directory. Returns comma-separated list prefixed with `idea-to-code:`. Prints warning to stderr if plugin not found.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k plugin_skills` passes with temp directory containing mock skill directories
  - Steps:
    - [x] Create `src/i2code/go_cmd/plugin_skills.py` — `list_plugin_skills(cache_dir=None) -> str` function matching `scripts/list-plugin-skills.sh`. Uses `os.environ.get("PLUGIN_CACHE_DIR", "~/.claude/plugins/cache")` if cache_dir not provided. Finds `*idea-to-code*/skills` directory, lists subdirectories, returns `"idea-to-code:skill1, idea-to-code:skill2"` format.
    - [x] Write pytest tests: finds skills in mock directory structure, returns empty string with stderr warning when plugin not found, respects `PLUGIN_CACHE_DIR` env var

- [x] **Task 4.2: Plan validator checks required task fields**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k plan_validator`
  - Observable: Parses plan markdown and validates each `- [ ] **Task X.Y:** ...` block contains `TaskType:`, `Entrypoint:`, `Observable:`, and `Evidence:` fields. Returns `(is_valid, errors)` tuple with specific error messages per missing field.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k plan_validator` passes with valid plans, plans missing fields, and edge cases
  - Steps:
    - [x] Create `src/i2code/go_cmd/plan_validator.py` — `validate_plan(plan_text: str) -> tuple[bool, list[str]]` function rewriting `scripts/make-plan.sh:22-66` AWK logic in Python. Scan lines for task headers (`- [ ] **Task X.Y:`), track which required fields appear before the next task header, report missing fields per task.
    - [x] Write pytest tests: valid plan passes, plan missing TaskType fails, plan missing Evidence fails, plan with multiple errors reports all, empty plan passes (no tasks to validate), plan with only completed tasks (`- [x]`) still validates

- [ ] **Task 4.3: `i2code plan create` generates, validates, and auto-repairs plan**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k create_plan`
  - Observable: Validates idea and spec exist. Enumerates plugin skills. Renders `create-implementation-plan.md` template with `$IDEA_FILE`, `$SPEC_FILE`, `$PLAN_SKILLS`. Invokes Claude in non-interactive mode (`-p` flag). Validates output plan. If validation fails, invokes Claude again with repair prompt (one attempt). Writes final plan to `{name}-plan.md`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k create_plan` passes with mocked ClaudeRunner for generation, validation, repair, and file write
  - Steps:
    - [ ] Create `src/i2code/go_cmd/create_plan.py` — `create_plan(project: IdeaProject, claude_runner, template_renderer, plugin_skills_fn, validator_fn)` function matching `scripts/make-plan.sh:104-119`. Uses `claude_runner.run_with_capture()` for non-interactive invocation with `-p` flag. Validates result, attempts one repair if invalid, writes to plan file.
    - [ ] Implement repair logic: construct repair prompt matching `scripts/make-plan.sh:73-101`, invoke Claude again with plan + errors, validate repaired plan
    - [ ] Write pytest tests: successful creation with valid plan, validation failure triggers repair, repair succeeds (valid after repair), repair fails (still invalid after repair — reports error), plan written to correct file path

- [ ] **Task 4.4: `i2code plan revise` revises plan via Claude**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k revise_plan`
  - Observable: Validates idea, spec, and plan files exist. Renders `revise-plan.md` template with `$IDEA_FILE`, `$SPEC_FILE`, `$PLAN_WITHOUT_STORIES_FILE`. Invokes Claude interactively.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k revise_plan` passes with mocked ClaudeRunner
  - Steps:
    - [ ] Create `src/i2code/go_cmd/revise_plan.py` — `revise_plan(project: IdeaProject, claude_runner, template_renderer)` function matching `scripts/revise-plan.sh`. Validates all three files, renders template, invokes Claude.
    - [ ] Write pytest tests: validates all three files, template rendered with correct variables, Claude invoked

- [ ] **Task 4.5: Wire plan commands, update orchestrator, delete bash scripts**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code plan create <dir>` and `i2code plan revise <dir>` invoke Python implementations. Orchestrator calls Python functions. Bash scripts deleted. Plugin skills bash test replaced by pytest. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes
  - Steps:
    - [ ] Check how `plan create` and `plan revise` are currently registered (they may be in `src/i2code/plan/cli.py` alongside existing plan management commands). Add direct Click commands there for `create` and `revise`, replacing any `script_command` registrations.
    - [ ] Update orchestrator: replace `run_script("make-plan.sh", ...)` and `run_script("revise-plan.sh", ...)` with direct Python function calls
    - [ ] Write CLI integration tests using CliRunner
    - [ ] Delete `src/i2code/scripts/make-plan.sh`, `src/i2code/scripts/revise-plan.sh`, `src/i2code/scripts/list-plugin-skills.sh`
    - [ ] Remove `test-scripts/test-list-plugin-skills.sh` from `test-scripts/test-end-to-end.sh` and delete it
    - [ ] Run `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 5: Design and Improve Commands

Migrate `create-design-doc.sh`, `analyze-sessions.sh`, `create-summary-reports.sh`, `review-issues.sh`, and `update-claude-files-from-project.sh`. These scripts range from simple (template + Claude) to moderately complex (argument parsing, date filtering, file discovery).

- [ ] **Task 5.1: `i2code design create` generates design document**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/design-cmd/ -v -m unit`
  - Observable: Validates idea and spec exist. Archives existing design file to `archive/` subdirectory with timestamp. Enumerates plugin skills. Renders `create-design-doc.md` template with `$IDEA_FILE`, `$DISCUSSION_FILE`, `$SPEC_FILE`, `$DESIGN_SKILLS`. Manages session (resume or new). Invokes Claude interactively.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/design-cmd/ -v -m unit` passes with mocked ClaudeRunner and filesystem
  - Steps:
    - [ ] Create `src/i2code/design_cmd/create_design.py` — `create_design(project: IdeaProject, claude_runner, template_renderer, session_manager, plugin_skills_fn)` matching `scripts/create-design-doc.sh`. Includes archive logic: if design file exists, move to `archive/<name>-design-<timestamp>.md`.
    - [ ] Update `src/i2code/design_cmd/cli.py`: replace `script_command` with direct Click command
    - [ ] Write pytest tests: validates files, archives existing design, template variables correct, session management, Claude invoked
    - [ ] Delete `src/i2code/scripts/create-design-doc.sh`

- [ ] **Task 5.2: `i2code improve analyze-sessions` analyzes Claude sessions**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k analyze`
  - Observable: Takes tracking directory argument. Validates sessions directory exists. Extracts session IDs from filenames, finds related issue files. Renders `analyze-sessions.md` template with `$SESSIONS_DIR`, `$ISSUES`, `$REPORT_FILE`. Invokes Claude non-interactively with `--add-dir` and `--allowedTools` flags.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k analyze` passes with mocked ClaudeRunner
  - Steps:
    - [ ] Create `src/i2code/improve/analyze_sessions.py` — `analyze_sessions(tracking_dir, claude_runner, template_renderer)` matching `scripts/analyze-sessions.sh`. Includes session ID extraction from filenames and issue file correlation.
    - [ ] Write pytest tests: validates directory, session ID extraction, issue file correlation, template rendering, Claude invoked with correct flags

- [ ] **Task 5.3: `i2code improve summary-reports` generates summary reports**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k summary`
  - Observable: Takes tracking directory and optional `--project-name` argument. Finds projects with sessions from today. For each project: gathers today's session and issue files, renders `create-summary-report.md` template, invokes Claude non-interactively with `--print` and `--add-dir` flags, saves output to `summary-reports/summary-<timestamp>.md`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k summary` passes with mocked ClaudeRunner and temp directory
  - Steps:
    - [ ] Create `src/i2code/improve/summary_reports.py` — `create_summary_reports(tracking_dir, claude_runner, template_renderer, *, project_name=None)` matching `scripts/create-summary-reports.sh`. Includes date filtering, project discovery, per-project report generation.
    - [ ] Write pytest tests: finds projects with today's sessions, filters by project name, creates reports directory, generates correct template variables, Claude invoked per project

- [ ] **Task 5.4: `i2code improve review-issues` reviews GitHub issues**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k review`
  - Observable: Takes HITL tracking directory. Accepts optional `--project` argument to restrict scope. Finds active issues from current year excluding `type: unknown`. Creates `resolved/` directories. Renders `review-issues.md` template with `$ACTIVE_ISSUES` and `$HITL_TRACKING_DIR`. Invokes Claude interactively.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k review` passes with mocked ClaudeRunner
  - Steps:
    - [ ] Create `src/i2code/improve/review_issues.py` — `review_issues(tracking_dir, claude_runner, template_renderer, *, project=None)` matching `scripts/review-issues.sh`. Includes argument parsing, issue filtering, `resolved/` directory creation.
    - [ ] Write pytest tests: finds active issues, excludes `type: unknown`, creates resolved dirs, respects `--project` filter, handles no issues found (exit 0)

- [ ] **Task 5.5: `i2code improve update-claude-files` updates Claude files from project**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k update_claude`
  - Observable: Takes project directory and `--config-dir` argument. Validates both directories exist and project has Claude files. Renders `update-claude-files-from-project.md` template with `$PROJECT_DIR`, `$PROJECT_CLAUDE_MD`, `$PROJECT_SETTINGS`, `$CONFIG_CLAUDE_MD`, `$CONFIG_SETTINGS`. Invokes Claude interactively.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k update_claude` passes with mocked ClaudeRunner
  - Steps:
    - [ ] Create `src/i2code/improve/update_claude_files.py` — `update_claude_files(project_dir, config_dir, claude_runner, template_renderer)` matching `scripts/update-claude-files-from-project.sh`. Validates Claude files exist in project.
    - [ ] Write pytest tests: validates directories, validates Claude files exist, template variables correct, Claude invoked

- [ ] **Task 5.6: Wire all improve and design commands, delete bash scripts**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: All improve and design subcommands invoke Python implementations. Bash scripts deleted. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes
  - Steps:
    - [ ] Update `src/i2code/improve/cli.py`: replace all `script_command` calls with direct Click commands for `analyze-sessions`, `summary-reports`, `review-issues`, and `update-claude-files`. Each command takes its arguments via Click options/arguments matching the bash script's interface.
    - [ ] Write CLI integration tests for all improve and design subcommands
    - [ ] Delete `src/i2code/scripts/analyze-sessions.sh`, `src/i2code/scripts/create-summary-reports.sh`, `src/i2code/scripts/review-issues.sh`, `src/i2code/scripts/update-claude-files-from-project.sh`, `src/i2code/scripts/create-design-doc.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 6: Setup Commands and Final Cleanup

Migrate `setup-claude-files.sh` and `update-project-claude-files.sh`. Then delete all remaining bash infrastructure.

- [ ] **Task 6.1: `i2code setup claude-files` copies Claude config files into project**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ -v -m unit -k claude_files`
  - Observable: Takes `--config-dir` argument. Copies `CLAUDE.md` from config dir to current directory. Creates `.claude/` directory and copies `settings.local.json`. This script does NOT invoke Claude — it is a pure file-copy operation.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ -v -m unit -k claude_files` passes with temp directory assertions
  - Steps:
    - [ ] Create `src/i2code/setup_cmd/claude_files.py` — `setup_claude_files(config_dir)` matching `scripts/setup-claude-files.sh`. Pure file operations: copy CLAUDE.md, create .claude/, copy settings.local.json.
    - [ ] Write pytest tests: copies files correctly, creates .claude directory, errors on missing config-dir

- [ ] **Task 6.2: `i2code setup update-project` pushes template updates into project**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ -v -m unit -k update_project`
  - Observable: Takes project directory and `--config-dir` arguments. Validates directories. Derives git repo root from config-dir. Extracts previous SHA from project's CLAUDE.md `claude-config-files-sha:` marker. Generates git diff between previous and current config-files SHA. Renders `update-project-claude-files.md` template with all variables. Invokes Claude interactively.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ -v -m unit -k update_project` passes with mocked subprocess and ClaudeRunner
  - Steps:
    - [ ] Create `src/i2code/setup_cmd/update_project.py` — `update_project(project_dir, config_dir, claude_runner, template_renderer)` matching `scripts/update-project-claude-files.sh`. Includes git SHA extraction, diff generation, template rendering.
    - [ ] Write pytest tests: validates directories, extracts SHA from CLAUDE.md, generates diff, handles first sync (no previous SHA), template variables correct, Claude invoked

- [ ] **Task 6.3: Wire setup commands, delete bash scripts**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `i2code setup claude-files` and `i2code setup update-project` invoke Python implementations. Bash scripts deleted. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes
  - Steps:
    - [ ] Update `src/i2code/setup_cmd/cli.py`: replace `script_command` calls with direct Click commands
    - [ ] Write CLI integration tests
    - [ ] Delete `src/i2code/scripts/setup-claude-files.sh` and `src/i2code/scripts/update-project-claude-files.sh`
    - [ ] Run `./test-scripts/test-end-to-end.sh`

- [ ] **Task 6.4: Delete remaining bash infrastructure**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `src/i2code/scripts/` directory deleted (including `_helper.sh`). `src/i2code/script_command.py` deleted. `src/i2code/script_runner.py` deleted. No `.sh` files remain under `src/`. All imports of `script_command` and `script_runner` removed. All tests pass. CI passes.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes and `find src/ -name "*.sh"` returns no results
  - Steps:
    - [ ] Delete `src/i2code/scripts/` directory (should contain only `_helper.sh` at this point — verify all other scripts are already deleted)
    - [ ] Delete `src/i2code/script_command.py`
    - [ ] Delete `src/i2code/script_runner.py`
    - [ ] Remove all imports of `script_command` and `script_runner` from `src/i2code/cli.py` and any other files (search with Grep)
    - [ ] Delete `tests/script-runner/` and `tests/script-command/` test directories (they test the now-deleted bash delegation infrastructure)
    - [ ] Remove any remaining bash test scripts from `test-scripts/` that tested migrated functionality (e.g., `test-subcommands-smoke.sh` if it tested bash-backed commands). Update `test-scripts/test-end-to-end.sh` accordingly.
    - [ ] Verify `find src/ -name "*.sh"` returns no results
    - [ ] Run `./test-scripts/test-end-to-end.sh`

---

## Change History
### 2026-02-26 14:30 - mark-step-complete
Added idea_file, spec_file, discussion_file, design_file, story_file, plan_with_stories_file, session_id_file, implement_config_file properties

### 2026-02-26 14:30 - mark-step-complete
Added validate_idea(), validate_spec(), validate_plan() methods

### 2026-02-26 14:30 - mark-step-complete
Created src/i2code/go_cmd/__init__.py

### 2026-02-26 14:30 - mark-step-complete
Created menu.py with get_user_choice function

### 2026-02-26 14:30 - mark-step-complete
Created orchestrator.py with Orchestrator class, detect_state, and menu_options_for

### 2026-02-26 14:30 - mark-step-complete
Created tests/go-cmd/ with 38 tests covering all four states, menu options, invalid input, and EOF

### 2026-02-26 14:30 - mark-task-complete
All 38 tests pass: state detection for 4 states, correct menu options, invalid input, EOF handling
