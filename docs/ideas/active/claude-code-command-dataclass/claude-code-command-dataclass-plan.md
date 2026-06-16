I have enough context to produce the plan. Outputting the plan to stdout now.

# Implementation Plan: Claude Code Command Dataclass

## Idea Type

**C. Platform/infrastructure capability** — internal refactor introducing a typed `ClaudeCodeCommand` description and a single `ClaudeRunner.execute()` entry point. No CLI flags or user-facing `i2code` commands change. Each steel thread below implements exactly one validation scenario (the primary scenario plus the secondary scenarios listed in `claude-code-command-dataclass-spec.md` §6) or one site-family migration that exercises a single capability surface.

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

### Project Test Commands

- Unit tests: `uv run --python 3.12 python3 -m pytest tests/ -m unit`
- Targeted unit tests: `uv run --python 3.12 python3 -m pytest <path-to-test-file> -v`
- Full end-to-end: `./test-scripts/test-end-to-end.sh`
- Type check: `uvx pyright --level error src/`

### Refactor Discipline

- This refactor introduces the new API alongside the old, migrates sites incrementally, then deletes the old API in the final steel thread. Do NOT delete `ClaudeRunner.run`, `run_interactive`, `run_batch`, `build_session_args`, or `get_or_create_session_args` until Steel Thread 15.
- After Steel Thread 15, a grep for `\["claude"` under `src/i2code/` MUST return zero matches (the only literal `"claude"` lives inside `ClaudeRunner.execute()`).
- For each migration task that touches a caller, update its existing pytest test to assert the caller now produces a `ClaudeCodeCommand` (recorded via `FakeClaudeRunner.calls`) instead of a `["claude", ...]` list.

---

## Steel Thread 1: Existing Test Suite Baseline

Establish a green baseline before any refactor changes so subsequent steel threads can be verified against a known-good starting point.

- [x] **Task 1.1: Existing unit test suite passes on master**
  - TaskType: INFRA
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/ -m unit`
  - Observable: pytest exits with code 0 and reports zero failures across all unit-marked tests; `uvx pyright --level error src/` reports zero errors.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/ -m unit` exits 0 and `uvx pyright --level error src/` exits 0 on the current working tree.
  - Steps:
    - [x] Run `uv run --python 3.12 python3 -m pytest tests/ -m unit` and confirm exit 0
    - [x] Run `uvx pyright --level error src/` and confirm exit 0
    - [x] If either fails, STOP and report the failure — do not begin the refactor on a red baseline

---

## Steel Thread 2: Plan generation flows through `ClaudeRunner.execute()` (primary scenario)

Implements the primary scenario from spec §6.1. Introduces `SessionId`, `ClaudeCodeCommand`, `ClaudeRunner.execute()` (batch path only at this stage — interactive path is added in Steel Thread 3), `ClaudeResult.result_text`, the result-text extraction inside `_parse_stream_json_output`, and migrates `src/i2code/go_cmd/create_plan.py` (both invocation site and stdout consumers).

- [x] **Task 2.1: `ClaudeCodeCommand` and `SessionId` dataclasses are defined in `claude_runner.py`**
  - TaskType: OUTCOME
  - Entrypoint: `from i2code.implement.claude_runner import ClaudeCodeCommand, SessionId`
  - Observable: `ClaudeCodeCommand` has fields `cwd: str`, `prompt: Optional[str] = None`, `interactive: Optional[bool] = None`, `allowed_tools: Optional[str] = None`, `session_id: Optional[SessionId] = None`, `add_dirs: list[str] = []`, `extra_args: list[str] = []`, `mock_command: Optional[list[str]] = None`. `SessionId` is a frozen dataclass with `session_id: str` and `is_new: bool`. Constructing `ClaudeCodeCommand(cwd="/x")` with neither `prompt` nor `mock_command` raises `ValueError`. Construction with `mock_command` and no `prompt` succeeds. Construction with both succeeds.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py -v -m unit` exits 0; new tests `test_claude_code_command_requires_prompt_or_mock`, `test_claude_code_command_mock_only_ok`, `test_session_id_frozen`.
  - Steps:
    - [x] Add new test class `TestClaudeCodeCommand` in `tests/implement/test_claude_runner.py` asserting field defaults, `ValueError` on missing prompt+mock_command, and the both-set case
    - [x] Add `SessionId(frozen=True)` dataclass to `src/i2code/implement/claude_runner.py`
    - [x] Add `ClaudeCodeCommand` dataclass with `__post_init__` validation as specified in §3.2 of the spec
    - [x] Run the targeted pytest and confirm green

- [x] **Task 2.2: `ClaudeResult.result_text` populated by `_parse_stream_json_output`**
  - TaskType: OUTCOME
  - Entrypoint: `run_claude_with_output_capture(cmd, cwd, debug=False)` (still public at this stage)
  - Observable: When stdout contains stream-json lines with `{"type": "result", "result": "<text>"}`, the returned `ClaudeResult.result_text` equals `"<text>"` (from the LAST such message). When stdout contains no stream-json `result` message, `result_text` equals the raw captured stdout verbatim.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestParseStreamJsonOutput -v -m unit` exits 0; new tests `test_result_text_from_terminal_result_message`, `test_result_text_falls_back_to_raw_stdout_when_no_result_message`.
  - Steps:
    - [x] Add `result_text: str = ""` to `ClaudeResult` dataclass in `src/i2code/implement/claude_runner.py:34`
    - [x] Write failing test that asserts `result_text` extraction from stream-json with one and multiple `type=result` messages, and the raw-stdout fallback case
    - [x] Modify `_parse_stream_json_output` at `src/i2code/implement/claude_runner.py:108` to also return the result-text value; modify `run_claude_with_output_capture` at `src/i2code/implement/claude_runner.py:134` to populate `ClaudeResult.result_text` from the parsed value
    - [x] Hoist the algorithm from `_extract_result_text` at `src/i2code/implement/pull_request_review_processor.py:457-470` into `_parse_stream_json_output` (do NOT delete the original yet — that happens in Steel Thread 8 once pull_request_review_processor is migrated)
    - [x] Run targeted pytest, confirm green

- [x] **Task 2.3: `ClaudeRunner.execute()` builds correct argv for the plan-generation scenario and dispatches to batch path**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=True, debug=False).execute(ClaudeCodeCommand(prompt=p, cwd=c, interactive=False, allowed_tools="Read(/repo/**)"))`
  - Observable: With `subprocess.Popen` patched, `Popen` is invoked once with positional args `["claude", "--verbose", "--output-format=stream-json", "--allowedTools", "Read(/repo/**)", "-p", p]` and `cwd=c`. The returned `ClaudeResult` includes `result_text` populated from the mocked stream-json `result` message.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute -v -m unit` exits 0; new test `test_execute_batch_with_allowed_tools_emits_expected_argv` patches `subprocess.Popen` and asserts the argv tuple and the resulting `result_text`.
  - Steps:
    - [x] Write failing test in `tests/implement/test_claude_runner.py` using `patch('subprocess.Popen')` that asserts argv, cwd, and `result_text`
    - [x] Add `execute(command: ClaudeCodeCommand) -> ClaudeResult` method to `ClaudeRunner` at `src/i2code/implement/claude_runner.py:248` following §3.3 ordered procedure
    - [x] Implement a private `_build_argv(command, effective_interactive)` helper on `ClaudeRunner` that follows steps 3a–3f from §3.3 (mock short-circuit, batch policy, allowed_tools, session_id, add_dirs, extra_args, prompt placement)
    - [x] Dispatch from `execute()` to existing `run_claude_with_output_capture` (batch) or `run_claude_interactive` (interactive); both functions remain at module scope as public for now (rename happens in Steel Thread 15)
    - [x] Run targeted pytest, confirm green

- [x] **Task 2.4: `FakeClaudeRunner.execute(command)` records calls in test fake**
  - TaskType: INFRA
  - Entrypoint: `FakeClaudeRunner().execute(ClaudeCodeCommand(prompt="x", cwd="/r", interactive=False))`
  - Observable: `fake.calls` records `("execute", command, "/r")` where `command` is the exact `ClaudeCodeCommand` instance passed. The fake returns the configured `ClaudeResult` (using the same default/configured-result mechanism as `run_interactive`/`run_batch`). Existing `run`/`run_interactive`/`run_batch` behaviour on the fake is unchanged.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestFakeClaudeRunner -v -m unit` exits 0; new tests `test_records_execute_call`, `test_execute_returns_configured_result`.
  - Steps:
    - [x] Write failing tests in `tests/implement/test_claude_runner.py` asserting `fake.calls` and configured-result behaviour for `execute`
    - [x] Add `execute(self, command) -> ClaudeResult` to `tests/implement/fake_claude_runner.py`
    - [x] Run targeted pytest, confirm green

- [x] **Task 2.5: `create_plan` builds a `ClaudeCodeCommand` and reads `result.result_text`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.go_cmd.create_plan.create_plan(project, claude_runner, services, repo_root=repo_root)`
  - Observable: With a `FakeClaudeRunner` injected and a configured `ClaudeResult(returncode=0, result_text=<valid plan>)`, `fake.calls` contains a single `("execute", cmd, repo_root)` entry where `cmd.prompt` equals the rendered `create-implementation-plan.md`, `cmd.interactive is False`, `cmd.allowed_tools` equals `build_read_only_tools_flag(repo_root)`, and `cmd.cwd == repo_root`. The plan file written at `project.plan_file` contains `result.result_text` (NOT `result.output.stdout`).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k "create_plan"` exits 0; an updated unit test for `create_plan` asserts both the `ClaudeCodeCommand` shape and that the plan file content equals `result.result_text`.
  - Steps:
    - [x] Update the existing `create_plan` unit test (under `tests/go-cmd/`) to assert the `("execute", ClaudeCodeCommand(...), cwd)` call shape and the use of `result_text`
    - [x] Replace `_generate_plan` in `src/i2code/go_cmd/create_plan.py:20` with a body that constructs a `ClaudeCodeCommand(prompt=rendered_prompt, cwd=cwd, interactive=False, allowed_tools=build_read_only_tools_flag(repo_root) if repo_root else None)` and calls `claude_runner.execute(...)`
    - [x] Change `src/i2code/go_cmd/create_plan.py:70` and `:78` from `result.output.stdout` to `result.result_text`
    - [x] Run targeted pytest, confirm green, then run full unit suite (`uv run --python 3.12 python3 -m pytest tests/ -m unit`) to confirm no regressions
    - [x] Run `uvx pyright --level error src/` and confirm zero errors

- [x] **Task 2.6: Real Claude integration test for ClaudeRunner.execute() batch path**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py -v -m integration_claude`
  - Observable: Invoking ClaudeRunner().execute(ClaudeCodeCommand(prompt=..., cwd=tmp_path, interactive=False, allowed_tools="Read(/dev/null)")) against the real claude CLI returns a ClaudeResult with returncode == 0, non-empty result_text, and result_text that does NOT start with { (proving the stream-json type=result message was extracted rather than the raw JSON stdout being returned verbatim).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py -m integration_claude -v exits 0; new test class TestClaudeRunnerExecuteRealClaude with test test_execute_batch_returns_result_text_from_real_claude.`
  - Steps:
    - [x] Add new test class TestClaudeRunnerExecuteRealClaude in tests/implement/test_claude_runner.py decorated with @pytest.mark.integration_claude (marker already registered in pytest.ini:6)
    - [x] Write test_execute_batch_returns_result_text_from_real_claude(tmp_path) that constructs a ClaudeCodeCommand with a deterministic prompt (e.g. Reply with exactly the word: pong), cwd=str(tmp_path), interactive=False, and a minimal allowed_tools flag, then calls ClaudeRunner().execute(cmd)
    - [x] Assert result.returncode == 0, result.result_text is non-empty, and result.result_text does not start with { (proving stream-json result extraction populated result_text rather than returning the raw JSON stdout)
    - [x] Run uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py -m integration_claude -v and confirm exit 0 (this requires claude on PATH and is excluded from the default -m unit run)

---

## Steel Thread 3: Interactive `create_design` with `--resume` (secondary scenario §6.2)

Adds the interactive dispatch path to `ClaudeRunner.execute()`, adds `--resume` rendering for `session_id.is_new=False`, introduces `read_session_id(path) -> Optional[SessionId]` in `session_manager.py`, and migrates `src/i2code/design_cmd/create_design.py`.

- [x] **Task 3.1: `ClaudeRunner.execute()` interactive path emits `["claude", prompt]` (no session)**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=True).execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=True))`
  - Observable: With `subprocess.run` patched, `subprocess.run` is invoked with positional args `["claude", "p"]` and `cwd="/c"`. No `--verbose`, no `--output-format=stream-json`, no `-p`. `ClaudeResult.result_text` equals `""` (interactive does not capture stdout).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_interactive_no_session -v -m unit` exits 0.
  - Steps:
    - [x] Write failing test patching `subprocess.run` and asserting argv + empty `result_text`
    - [x] Update `_build_argv` and `execute()` in `src/i2code/implement/claude_runner.py` so the interactive branch appends `command.prompt` positionally (no `-p`)
    - [x] Run targeted pytest, confirm green

- [ ] **Task 3.2: `ClaudeRunner.execute()` interactive path renders `--resume <id>` for `is_new=False`**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=True).execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=True, session_id=SessionId("abc123", is_new=False)))`
  - Observable: `subprocess.run` is invoked with `["claude", "--resume", "abc123", "p"]`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_interactive_with_resume -v -m unit` exits 0.
  - Steps:
    - [ ] Write failing test asserting argv with `--resume`
    - [ ] Extend `_build_argv` in `src/i2code/implement/claude_runner.py` to render `["--resume", session_id.session_id]` when `command.session_id is not None and not command.session_id.is_new`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 3.3: `read_session_id(path) -> Optional[SessionId]` in `session_manager.py`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.session_manager.read_session_id(path)` (NEW typed variant returning `Optional[SessionId]`)
  - Observable: When `path` exists with a UUID, the function returns `SessionId(session_id=<uuid>, is_new=False)`. When `path` does not exist, returns `None`. The existing private string-returning `read_session_id` helper is renamed to a private name to avoid the type clash.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/ -m unit -k "session_manager and read_session_id" -v` exits 0; new tests `test_read_session_id_returns_session_id_dataclass_when_file_present`, `test_read_session_id_returns_none_when_file_absent`.
  - Steps:
    - [ ] Rename the existing string-returning `read_session_id` at `src/i2code/session_manager.py:8` to `_read_session_id_str` (internal helper)
    - [ ] Update internal callers in `src/i2code/session_manager.py` (`build_session_args`, `get_or_create_session_args`) to use `_read_session_id_str` so they still function
    - [ ] Write failing test asserting `SessionId` return type and `None` case
    - [ ] Add new public `read_session_id(path: str) -> Optional[SessionId]` to `src/i2code/session_manager.py` returning `SessionId(id, is_new=False)` or `None`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 3.4: `create_design` builds a `ClaudeCodeCommand` with `session_id` from `read_session_id`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.design_cmd.create_design.create_design(project, claude_runner, ...)`
  - Observable: With a `FakeClaudeRunner` injected, when the session file exists, `fake.calls` records one `("execute", cmd, project.directory)` where `cmd.session_id == SessionId(<id>, is_new=False)`, `cmd.prompt` equals the rendered design prompt, `cmd.interactive is True`. When the session file does not exist, `cmd.session_id is None`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/design-cmd/ -v -m unit -k "create_design"` exits 0; updated test asserts both the with-session and without-session `ClaudeCodeCommand` shapes.
  - Steps:
    - [ ] Update the existing `create_design` unit test to assert the `ClaudeCodeCommand` shape (both with and without session file)
    - [ ] Replace argv assembly at `src/i2code/design_cmd/create_design.py:63` with `claude_runner.execute(ClaudeCodeCommand(prompt=prompt, cwd=project.directory, interactive=True, session_id=read_session_id(project.session_id_file)))`
    - [ ] Run targeted pytest and full unit suite; both green
    - [ ] Run `uvx pyright --level error src/`; zero errors

---

## Steel Thread 4: Interactive `brainstorm` with `--session-id` or `--resume` (secondary scenario §6.2)

Adds `--session-id` rendering for `session_id.is_new=True`, introduces `read_or_create_session(path) -> SessionId`, and migrates `src/i2code/idea_cmd/brainstorm.py`.

- [ ] **Task 4.1: `ClaudeRunner.execute()` renders `--session-id <id>` for `is_new=True`**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=True).execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=True, session_id=SessionId("newid", is_new=True)))`
  - Observable: `subprocess.run` is invoked with `["claude", "--session-id", "newid", "p"]`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_with_new_session_id -v -m unit` exits 0.
  - Steps:
    - [ ] Write failing test asserting argv with `--session-id`
    - [ ] Extend `_build_argv` so `command.session_id.is_new=True` renders `["--session-id", session_id.session_id]`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 4.2: `read_or_create_session(path) -> SessionId` in `session_manager.py`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.session_manager.read_or_create_session(path)`
  - Observable: When `path` exists, returns `SessionId(<id>, is_new=False)` without writing. When `path` does not exist, generates a UUID, writes it to `path`, and returns `SessionId(<new_uuid>, is_new=True)`. The written content equals the returned `session_id`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/ -m unit -k "session_manager and read_or_create_session" -v` exits 0; new tests `test_read_or_create_returns_existing_session`, `test_read_or_create_creates_new_session_and_writes_file`.
  - Steps:
    - [ ] Write failing tests covering both branches (existing file, missing file)
    - [ ] Add `read_or_create_session(path: str) -> SessionId` to `src/i2code/session_manager.py`, calling existing `_read_session_id_str` and `create_session_id` helpers
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 4.3: `brainstorm` builds a `ClaudeCodeCommand` with session and allowed_tools**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.idea_cmd.brainstorm.brainstorm(project, claude_runner, ..., repo_root=repo_root)`
  - Observable: With a `FakeClaudeRunner`, `fake.calls` records one `("execute", cmd, cwd)` where `cmd.prompt` equals the rendered brainstorm prompt, `cmd.interactive is True`, `cmd.allowed_tools` equals `build_allowed_tools_flag(repo_root, project.directory)` (or `None` when `repo_root is None`), and `cmd.session_id` is the `SessionId` returned by `read_or_create_session(project.session_id_file)`. After invocation, the session-id file at `project.session_id_file` exists and contains a UUID.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/idea-cmd/ -v -m unit -k "brainstorm"` exits 0; updated brainstorm unit test asserts the `ClaudeCodeCommand` shape and side-effect on session file.
  - Steps:
    - [ ] Update existing brainstorm unit test to assert the `ClaudeCodeCommand` shape and the session-file side effect
    - [ ] Replace argv assembly at `src/i2code/idea_cmd/brainstorm.py:88` with a single `claude_runner.execute(ClaudeCodeCommand(...))` call using `read_or_create_session(project.session_id_file)`
    - [ ] Run targeted pytest and full unit suite; both green
    - [ ] Run `uvx pyright --level error src/`; zero errors

---

## Steel Thread 5: `summary_reports` batch with `--add-dir` and `--allowedTools` (secondary scenario §6.2)

Adds `add_dirs` rendering to `ClaudeRunner.execute()` and migrates `src/i2code/improve/summary_reports.py` (including the second `result.result_text` consumer).

- [ ] **Task 5.1: `ClaudeRunner.execute()` renders `--add-dir <path>` for each entry in `add_dirs`**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner().execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=False, allowed_tools="Read", add_dirs=["/d1", "/d2"]))`
  - Observable: `subprocess.Popen` is invoked with `["claude", "--verbose", "--output-format=stream-json", "--allowedTools", "Read", "--add-dir", "/d1", "--add-dir", "/d2", "-p", "p"]`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_with_add_dirs -v -m unit` exits 0; new test asserts argv ordering for one and two `add_dirs`.
  - Steps:
    - [ ] Write failing test asserting argv with one and with two `--add-dir` entries
    - [ ] Extend `_build_argv` to emit `--add-dir <path>` per entry, AFTER session flags and BEFORE `extra_args` and the prompt (per §3.3 ordered procedure)
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 5.2: `summary_reports` builds a `ClaudeCodeCommand` and writes `result.result_text` to the report file**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.improve.summary_reports.generate_summary_report(...)` (the function at `src/i2code/improve/summary_reports.py:134`)
  - Observable: With `FakeClaudeRunner` configured with `ClaudeResult(result_text="REPORT BODY")`, `fake.calls` records one `("execute", cmd, project_dir)` where `cmd.interactive is False`, `cmd.allowed_tools == "Read"`, `cmd.add_dirs == [project_dir]`. The file at the report output path contains exactly `"REPORT BODY"` (NOT the raw stdout).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k "summary_reports"` exits 0.
  - Steps:
    - [ ] Update the existing summary_reports unit test to assert the `ClaudeCodeCommand` shape and that the written file content equals `result.result_text`
    - [ ] Replace argv assembly at `src/i2code/improve/summary_reports.py:134` with `claude_runner.execute(ClaudeCodeCommand(prompt=rendered, cwd=project_dir, interactive=False, allowed_tools="Read", add_dirs=[project_dir]))`
    - [ ] Change `src/i2code/improve/summary_reports.py:145` from `result.output.stdout` to `result.result_text`
    - [ ] Run targeted pytest, confirm green

---

## Steel Thread 6: `analyze_sessions` batch with multiple `--add-dir` (secondary scenario §6.2)

Validates multi-`add-dir` rendering with `allowed_tools="Read,Edit,Write"` and migrates `src/i2code/improve/analyze_sessions.py`. This caller writes its report file directly via Claude, so `result.result_text` is discarded — verifies the spec's Q9 condition.

- [ ] **Task 6.1: `analyze_sessions` builds a `ClaudeCodeCommand` with two `add_dirs`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.improve.analyze_sessions.analyze_sessions(...)` (the function at `src/i2code/improve/analyze_sessions.py:93`)
  - Observable: With `FakeClaudeRunner`, `fake.calls` records one `("execute", cmd, tracking_dir)` where `cmd.interactive is False`, `cmd.allowed_tools == "Read,Edit,Write"`, `cmd.add_dirs == [sessions_dir, issues_dir]` (preserving today's order at `analyze_sessions.py:93`). The caller does NOT consume `result.result_text` or `result.output.stdout` for the report body (the report is written by Claude itself).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k "analyze_sessions"` exits 0.
  - Steps:
    - [ ] Update existing analyze_sessions unit test to assert the `ClaudeCodeCommand` shape with two `add_dirs` and that stdout content is NOT read by the caller
    - [ ] Replace argv assembly at `src/i2code/improve/analyze_sessions.py:93` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

---

## Steel Thread 7: Worktree task execution with mode inheritance via `CommandBuilder.build_task_command` (secondary scenario §6.2)

Implements the third secondary scenario from §6.2: a `CommandBuilder.build_task_command` call returns a `ClaudeCodeCommand` with `interactive=None`, and `ClaudeRunner.execute()` resolves the mode from the runner's `__init__` setting. Migrates `worktree_mode.py:204` and `trunk_mode.py:72`.

- [ ] **Task 7.1: `ClaudeRunner.execute()` resolves `command.interactive=None` from runner's `_interactive`**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=False).execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=None))` and `ClaudeRunner(interactive=True).execute(ClaudeCodeCommand(prompt="p", cwd="/c", interactive=None))`
  - Observable: First case dispatches to the batch path (`subprocess.Popen` with `--verbose --output-format=stream-json -p p`). Second case dispatches to the interactive path (`subprocess.run` with `claude p`).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_mode_inherited_from_runner -v -m unit` exits 0; parameterized test covering both cases.
  - Steps:
    - [ ] Write failing parameterized test covering both `interactive=None` resolutions
    - [ ] Verify `execute()` already implements `effective_interactive = command.interactive if command.interactive is not None else self._interactive` from Task 2.3; adjust if missing
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 7.2: `CommandBuilder.build_task_command` returns a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_task_command(idea_directory, task_description, opts, cwd=working_tree_dir)`
  - Observable: Returns a `ClaudeCodeCommand` whose `prompt` equals the rendered `task_execution.j2`, `cwd == working_tree_dir`, `interactive == opts.interactive` mapped to `Optional[bool]`. Any `--allowedTools <value>` pair found in `opts.extra_cli_args` is routed into `allowed_tools`; any `--add-dir <value>` pair is routed into `add_dirs`; remaining tokens stay in `extra_args`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_task_command"` exits 0; new tests `test_build_task_command_returns_dataclass`, `test_build_task_command_splits_allowed_tools_from_extra_cli_args`, `test_build_task_command_splits_add_dir_from_extra_cli_args`.
  - Steps:
    - [ ] Update existing `test_command_builder.py` `build_task_command` tests to assert `ClaudeCodeCommand` return type and field values; add new tests for the splitter logic
    - [ ] Add `cwd: str` parameter to `CommandBuilder.build_task_command` at `src/i2code/implement/command_builder.py:80`
    - [ ] Implement a private `_split_extra_cli_args(extra_cli_args)` helper on `CommandBuilder` that returns `(allowed_tools, add_dirs, extra_args)` by recognising `--allowedTools <value>` and `--add-dir <value>` pairs
    - [ ] Replace the body of `build_task_command` to render the prompt and return a `ClaudeCodeCommand`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 7.3: `worktree_mode` and `trunk_mode` invoke `execute()` with the `ClaudeCodeCommand` from `build_task_command`**
  - TaskType: OUTCOME
  - Entrypoint: `WorktreeMode.run_task(...)` (call site at `src/i2code/implement/worktree_mode.py:204`) and `TrunkMode.run_task(...)` (call site at `src/i2code/implement/trunk_mode.py:72`)
  - Observable: With a `FakeClaudeRunner` (configured with `interactive=False` for non-interactive runs), `fake.calls` records `("execute", cmd, working_tree_dir)` where `cmd` was returned verbatim by `CommandBuilder.build_task_command`. `subprocess` is invoked with the argv that `_build_argv` produces from that command.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_worktree_mode.py tests/implement/test_trunk_mode.py -v -m unit` exits 0.
  - Steps:
    - [ ] Update `test_worktree_mode.py` and `test_trunk_mode.py` task-execution tests to assert the `("execute", ClaudeCodeCommand, cwd)` recorded call
    - [ ] Replace `run_batch`/`run_interactive`/`run` calls at `src/i2code/implement/worktree_mode.py:204` and `src/i2code/implement/trunk_mode.py:72` with `claude_runner.execute(command)` where `command` is the `ClaudeCodeCommand` returned by `build_task_command`
    - [ ] Run targeted pytest, confirm green

---

## Steel Thread 8: Mock-binary triage short-circuit via `mock_command` (secondary scenario §6.2)

Implements the mock-binary triage scenario from §6.2 and finishes the migration of `pull_request_review_processor.py` for the triage path. Also removes the now-dead `_extract_result_text` private helper since `result.result_text` is populated by `_parse_stream_json_output`.

- [ ] **Task 8.1: `ClaudeRunner.execute()` mock short-circuit dispatches `mock_command` argv as-is**
  - TaskType: OUTCOME
  - Entrypoint: `ClaudeRunner(interactive=False).execute(ClaudeCodeCommand(cwd="/c", mock_command=["/path/mock-claude", "triage-42"]))`
  - Observable: `subprocess.Popen` (or `subprocess.run` if runner's `_interactive=True`) is invoked with positional args `["/path/mock-claude", "triage-42"]` exactly — no `claude`, no `--verbose`, no `-p`, no extra arguments. `cwd="/c"`. All other `ClaudeCodeCommand` fields are ignored.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_claude_runner.py::TestClaudeRunnerExecute::test_execute_mock_command_short_circuit -v -m unit` exits 0; new test parameterised over batch and interactive runner modes.
  - Steps:
    - [ ] Write failing test asserting verbatim argv dispatch for both batch and interactive runner modes
    - [ ] Implement step 1 of §3.3 in `ClaudeRunner.execute()` — when `command.mock_command is not None`, dispatch the argv as-is using the runner's default mode (`self._interactive`); skip all subsequent steps
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 8.2: `CommandBuilder.build_triage_command` returns a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_triage_command(feedback_content, cwd=working_tree_dir, interactive=False)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("triage_feedback.j2", ...)`, `cwd=working_tree_dir`, `interactive=False`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_triage_command"` exits 0.
  - Steps:
    - [ ] Update existing `build_triage_command` tests to assert the `ClaudeCodeCommand` return type
    - [ ] Add `cwd: str` parameter and replace the `_with_mode` call at `src/i2code/implement/command_builder.py:143` with a `ClaudeCodeCommand` constructor
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 8.3: `pull_request_review_processor` triage path uses `execute()` and consumes `result.result_text`**
  - TaskType: OUTCOME
  - Entrypoint: `PullRequestReviewProcessor.process_triage(pr_number, ...)` (the path covering `src/i2code/implement/pull_request_review_processor.py:227-230`)
  - Observable: When `self._opts.mock_claude` is set, `fake.calls` records `("execute", ClaudeCodeCommand(cwd=working_tree_dir, mock_command=[mock_path, f"triage-{pr_number}"]))`. When `mock_claude` is unset, `fake.calls` records `("execute", <CommandBuilder.build_triage_command(...)>)` verbatim. The processor reads triage output from `result.result_text` (NOT from a private call to `_extract_result_text`). `_extract_result_text` is no longer defined in `pull_request_review_processor.py`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_pull_request_review_processor.py -v -m unit -k "triage"` exits 0; updated tests cover both mock and non-mock paths.
  - Steps:
    - [ ] Update triage-path tests in `tests/implement/test_pull_request_review_processor.py` to assert the new `("execute", ClaudeCodeCommand)` call shape (both mock and non-mock) and to assert reads from `result.result_text`
    - [ ] Update `src/i2code/implement/pull_request_review_processor.py:227-228` (mock branch) to construct `ClaudeCodeCommand(cwd=..., mock_command=[mock_path, f"triage-{pr_number}"])`
    - [ ] Update `src/i2code/implement/pull_request_review_processor.py:230` (non-mock branch) to call `CommandBuilder().build_triage_command(feedback_content, cwd=..., interactive=False)`
    - [ ] Replace the call to `claude_runner.run_batch(triage_cmd, cwd=...)` with `claude_runner.execute(cmd)`
    - [ ] Replace the private `_extract_result_text(...)` call (around `pull_request_review_processor.py:457-470`) with a read of `result.result_text` from the `ClaudeResult` already returned
    - [ ] Delete the `_extract_result_text` private function at `src/i2code/implement/pull_request_review_processor.py:457-470`
    - [ ] Run targeted pytest and full unit suite; both green
    - [ ] Run `uvx pyright --level error src/`; zero errors

---

## Steel Thread 9: `build_fix_command` migration finishes `pull_request_review_processor`

Migrates the fix-path in `pull_request_review_processor.py` (both mock-binary short-circuit at `:317-318` and non-mock call at `:323`). Same pattern as Steel Thread 8 but for the fix command.

- [ ] **Task 9.1: `CommandBuilder.build_fix_command` returns a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_fix_command(pr_url, feedback_content, fix_description, cwd=working_tree_dir, interactive=False)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("fix_feedback.j2", ...)`, `cwd=working_tree_dir`, `interactive=False`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_fix_command"` exits 0.
  - Steps:
    - [ ] Update tests for `build_fix_command` to assert dataclass return
    - [ ] Add `cwd: str` parameter and replace body at `src/i2code/implement/command_builder.py:165` with a `ClaudeCodeCommand` constructor
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 9.2: `pull_request_review_processor` fix path uses `execute()` for mock and non-mock branches**
  - TaskType: OUTCOME
  - Entrypoint: `PullRequestReviewProcessor.process_fix_group(pr_url, comment_ids, fix_description, ...)` (the path covering `src/i2code/implement/pull_request_review_processor.py:317-323`)
  - Observable: When `self._opts.mock_claude` is set, `fake.calls` records `("execute", ClaudeCodeCommand(cwd=working_tree_dir, mock_command=[mock_path, f"fix-{pr_number}-{comment_ids[0]}"]))`. When unset, the recorded `ClaudeCodeCommand` matches the output of `build_fix_command(pr_url, feedback_content, fix_description, cwd=working_tree_dir, interactive=False)`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_pull_request_review_processor.py -v -m unit -k "fix"` exits 0.
  - Steps:
    - [ ] Update fix-path tests to assert the new call shape (both mock and non-mock branches)
    - [ ] Update `src/i2code/implement/pull_request_review_processor.py:317-318` (mock branch) to construct `ClaudeCodeCommand(cwd=..., mock_command=[mock_path, f"fix-{pr_number}-{comment_ids[0]}"])`
    - [ ] Update `src/i2code/implement/pull_request_review_processor.py:323` (non-mock branch) to call `CommandBuilder().build_fix_command(pr_url, feedback_content, fix_description, cwd=..., interactive=False)`
    - [ ] Replace `run_batch`/`run_interactive` dispatch with `claude_runner.execute(cmd)`
    - [ ] Run targeted pytest and full unit suite; both green

---

## Steel Thread 10: `build_recovery_command` migration

Migrates `commit_recovery.py:48`. This is a non-mock single-site migration; it exercises `CommandBuilder` plumbing established earlier.

- [ ] **Task 10.1: `CommandBuilder.build_recovery_command` returns a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_recovery_command(plan_file, diff_summary, cwd=working_tree_dir, interactive=True)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("commit_recovery.j2", ...)`, `cwd=working_tree_dir`, `interactive=True` (or `False` as supplied).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_recovery_command"` exits 0.
  - Steps:
    - [ ] Update existing tests for `build_recovery_command` to assert dataclass return type
    - [ ] Add `cwd: str` parameter and replace body at `src/i2code/implement/command_builder.py:54` with a `ClaudeCodeCommand` constructor
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 10.2: `commit_recovery` invokes `execute()` with the `ClaudeCodeCommand` from `build_recovery_command`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.implement.commit_recovery.recover_commit(plan_file, diff_summary, claude_runner, cwd, ...)` (call site at `src/i2code/implement/commit_recovery.py:48`)
  - Observable: `fake.calls` records `("execute", cmd, cwd)` where `cmd` is verbatim from `build_recovery_command`. Reads of `result.output.stdout` at `commit_recovery.py:63` are NOT changed (per spec Q9 — this site continues using raw stdout for diagnostic, not result-text).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_commit_recovery.py -v -m unit` exits 0.
  - Steps:
    - [ ] Update `test_commit_recovery.py` tests to assert the new call shape
    - [ ] Update `src/i2code/implement/commit_recovery.py:48` to call `build_recovery_command(plan_file, diff_summary, cwd=cwd, interactive=...)` and `claude_runner.execute(...)`
    - [ ] Confirm `src/i2code/implement/commit_recovery.py:63` continues to read `result.output.stdout` (unchanged per spec)
    - [ ] Run targeted pytest and full unit suite; both green

---

## Steel Thread 11: `build_scaffolding_command` migration removes the `mock_claude` parameter

Migrates `project_scaffolding.py:35` and the mock short-circuit at `command_builder.py:124-125`. The `mock_claude` parameter is REMOVED from `build_scaffolding_command` and the mock pattern moves to the caller.

- [ ] **Task 11.1: `CommandBuilder.build_scaffolding_command` returns a `ClaudeCodeCommand` and no longer accepts `mock_claude`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_scaffolding_command(idea_directory, cwd=working_tree_dir, interactive=False)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("scaffolding.j2", ...)`, `cwd=working_tree_dir`, `interactive=False`, `allowed_tools="Write,Read,Edit,Bash(gradle --version),Bash(mkdir -p:*)"`. The `mock_claude` parameter is gone — calling with it raises `TypeError`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_scaffolding_command"` exits 0; new test `test_build_scaffolding_command_no_longer_accepts_mock_claude`.
  - Steps:
    - [ ] Update existing `build_scaffolding_command` tests to drop the `mock_claude` argument and assert dataclass return; add `TypeError` test for `mock_claude=` kwarg
    - [ ] Add `cwd: str` parameter and replace body at `src/i2code/implement/command_builder.py:108` with `ClaudeCodeCommand(prompt=..., cwd=..., interactive=False, allowed_tools="Write,Read,Edit,Bash(gradle --version),Bash(mkdir -p:*)")` for the batch case and `ClaudeCodeCommand(prompt=..., cwd=..., interactive=True)` for interactive
    - [ ] DELETE the `mock_claude` parameter from `build_scaffolding_command`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 11.2: `project_scaffolding` builds mock or real `ClaudeCodeCommand` at the caller**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.implement.project_scaffolding.run_scaffolding(idea_directory, claude_runner, mock_claude=None, cwd=working_tree_dir)` (call site at `src/i2code/implement/project_scaffolding.py:35`)
  - Observable: When `mock_claude` is set, `fake.calls` records `("execute", ClaudeCodeCommand(cwd=working_tree_dir, mock_command=[mock_claude, "setup"]))`. When unset, the recorded command matches the output of `build_scaffolding_command(idea_directory, cwd=working_tree_dir, interactive=False)`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_project_scaffolding.py -v -m unit` exits 0.
  - Steps:
    - [ ] Update `test_project_scaffolding.py` tests to assert both mock and non-mock branches construct the right `ClaudeCodeCommand`
    - [ ] In `src/i2code/implement/project_scaffolding.py:35`, wrap the call with a branch: if `mock_claude` is set, construct `ClaudeCodeCommand(cwd=..., mock_command=[mock_claude, "setup"])`; else call `build_scaffolding_command(...)`
    - [ ] Replace dispatch with `claude_runner.execute(cmd)`
    - [ ] Run targeted pytest and full unit suite; both green

---

## Steel Thread 12: `build_ci_fix_command` migration

Migrates `github_actions_build_fixer.py` (`build_ci_fix_command` site at `:138-139`, both mock and non-mock branches).

- [ ] **Task 12.1: `CommandBuilder.build_ci_fix_command` returns a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_ci_fix_command(run_id, workflow_name, failure_logs, cwd=working_tree_dir, interactive=False)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("ci_fix.j2", ...)`, `cwd=working_tree_dir`, `interactive=False`. Failure-log truncation at `command_builder.py:212-213` is preserved.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_ci_fix_command"` exits 0.
  - Steps:
    - [ ] Update existing tests to assert dataclass return
    - [ ] Add `cwd: str` parameter and replace body at `src/i2code/implement/command_builder.py:193` with a `ClaudeCodeCommand` constructor (preserving the `max_log_length` truncation)
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 12.2: `github_actions_build_fixer` invokes `execute()` for both mock and non-mock branches**
  - TaskType: OUTCOME
  - Entrypoint: `GithubActionsBuildFixer.fix_failing_run(run_id, ...)` (the path covering `src/i2code/implement/github_actions_build_fixer.py:138-139`)
  - Observable: When mock is set, `fake.calls` records `("execute", ClaudeCodeCommand(cwd=working_tree_dir, mock_command=[mock_path, f"fix-ci-{run_id}"]))`. When unset, matches `build_ci_fix_command(...)` output.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_github_actions_build_fixer.py -v -m unit` exits 0.
  - Steps:
    - [ ] Update tests to assert both branches' call shapes
    - [ ] Update `src/i2code/implement/github_actions_build_fixer.py:138-139` to construct mock or real `ClaudeCodeCommand` and call `claude_runner.execute(cmd)`
    - [ ] Run targeted pytest and full unit suite; both green

---

## Steel Thread 13: Remaining simple interactive callers migrate to `execute()`

Migrates the six remaining interactive direct-argv sites. They all share the simple pattern `claude_runner.execute(ClaudeCodeCommand(prompt=..., cwd=..., interactive=True))` (plus optional `allowed_tools`). No new capability surface is introduced — this thread sweeps remaining sites so Steel Thread 15 can delete the old API.

- [ ] **Task 13.1: `setup_cmd/update_project` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.setup_cmd.update_project.update_project(project, claude_runner, ...)` (call site at `src/i2code/setup_cmd/update_project.py:154`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` where `cmd.interactive is True` and `cmd.prompt` equals the rendered prompt from the existing template. No raw `["claude", ...]` list is constructed.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/setup-cmd/ -v -m unit -k "update_project"` exits 0.
  - Steps:
    - [ ] Update existing `update_project` unit test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/setup_cmd/update_project.py:154` with a single `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 13.2: `spec_cmd/create_spec` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.spec_cmd.create_spec.create_spec(project, claude_runner, ...)` (call site at `src/i2code/spec_cmd/create_spec.py:42`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` with `cmd.interactive is True` and `cmd.prompt` equals the rendered create-spec prompt. Any allowed_tools currently in the argv become `cmd.allowed_tools`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit -k "create_spec"` exits 0.
  - Steps:
    - [ ] Update existing test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/spec_cmd/create_spec.py:42` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 13.3: `spec_cmd/revise_spec` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.spec_cmd.revise_spec.revise_spec(project, claude_runner, ...)` (call site at `src/i2code/spec_cmd/revise_spec.py:47`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` with `cmd.interactive is True` and `cmd.prompt` equals the rendered revise-spec prompt.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/ -v -m unit -k "revise_spec"` exits 0.
  - Steps:
    - [ ] Update existing test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/spec_cmd/revise_spec.py:47` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 13.4: `go_cmd/revise_plan` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.go_cmd.revise_plan.revise_plan(project, claude_runner, ...)` (call site at `src/i2code/go_cmd/revise_plan.py:36`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` with `cmd.interactive is True` and `cmd.prompt` equals the rendered revise-plan prompt.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/ -v -m unit -k "revise_plan"` exits 0.
  - Steps:
    - [ ] Update existing test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/go_cmd/revise_plan.py:36` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 13.5: `improve/review_issues` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.improve.review_issues.review_issues(...)` (call site at `src/i2code/improve/review_issues.py:117`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` with `cmd.interactive is True` and `cmd.prompt` equals the rendered review-issues prompt.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k "review_issues"` exits 0.
  - Steps:
    - [ ] Update existing test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/improve/review_issues.py:117` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 13.6: `improve/update_claude_files` invokes `execute()` with a `ClaudeCodeCommand`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code.improve.update_claude_files.update_claude_files(...)` (call site at `src/i2code/improve/update_claude_files.py:58`)
  - Observable: `fake.calls` records one `("execute", cmd, cwd)` with `cmd.interactive is True` and `cmd.prompt` equals the rendered prompt.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/improve/ -v -m unit -k "update_claude_files"` exits 0.
  - Steps:
    - [ ] Update existing test to assert the `ClaudeCodeCommand` shape
    - [ ] Replace argv assembly at `src/i2code/improve/update_claude_files.py:58` with `claude_runner.execute(ClaudeCodeCommand(...))`
    - [ ] Run targeted pytest, confirm green
    - [ ] After this task: confirm with `grep -R '\["claude"' src/i2code/ --include='*.py'` that the only remaining match is inside `src/i2code/implement/command_builder.py` (`build_feedback_command`, fixed in Steel Thread 14)

---

## Steel Thread 14: `build_feedback_command` returns a `ClaudeCodeCommand` with `extra_args` (preserves issue #40)

Migrates the last `CommandBuilder` method. Issue #40 (broken `--print wt-handle-feedback.md` argv shape) is INTENTIONALLY preserved via the `extra_args` escape hatch per spec §3.8 and §6.2 last bullet.

- [ ] **Task 14.1: `build_feedback_command` returns a `ClaudeCodeCommand(..., extra_args=["--print", "wt-handle-feedback.md"])`**
  - TaskType: OUTCOME
  - Entrypoint: `CommandBuilder().build_feedback_command(pr_url, feedback_type, feedback_content, cwd=working_tree_dir)`
  - Observable: Returns a `ClaudeCodeCommand` with `prompt = render_template("address_feedback.j2", ...)`, `cwd=working_tree_dir`, `interactive=False`, `extra_args=["--print", "wt-handle-feedback.md"]`. When dispatched through `ClaudeRunner.execute()`, the emitted argv is `["claude", "--verbose", "--output-format=stream-json", "--print", "wt-handle-feedback.md", "-p", <prompt>]` — the same broken 2-token shape as today (issue #40 preserved).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -v -m unit -k "build_feedback_command"` exits 0; new test `test_build_feedback_command_preserves_issue_40_via_extra_args` asserts the emitted argv via `_build_argv` against the verbatim 2-token shape.
  - Steps:
    - [ ] Update existing test for `build_feedback_command` to assert dataclass return AND assert the verbatim `extra_args=["--print", "wt-handle-feedback.md"]` shape; add the cross-check test that runs `ClaudeRunner._build_argv` against the returned command and asserts the full argv list
    - [ ] Add `cwd: str` parameter and replace body at `src/i2code/implement/command_builder.py:225` with `ClaudeCodeCommand(prompt=rendered, cwd=cwd, interactive=False, extra_args=["--print", "wt-handle-feedback.md"])`
    - [ ] Update the feedback-command caller (search for `build_feedback_command` invocations in `src/i2code/implement/`) to pass `cwd=working_tree_dir` and to call `claude_runner.execute(cmd)` instead of `run_batch`/`run_interactive`
    - [ ] Run targeted pytest and full unit suite; both green
    - [ ] After this task: confirm with `grep -R '\["claude"' src/i2code/ --include='*.py'` that the ONLY remaining matches are inside `src/i2code/implement/claude_runner.py` (the canonical `["claude"]` in `_build_argv`)

---

## Steel Thread 15: Remove old API (`run`, `run_interactive`, `run_batch`, `build_session_args`, `get_or_create_session_args`, `_with_mode`); rename module-level functions to private

Final cleanup step. Removes all deprecated symbols and renames the module-level dispatch functions to mark them private. Satisfies §3.6 and acceptance criteria 1–8 in §8.

- [ ] **Task 15.1: Remove `ClaudeRunner.run`, `run_interactive`, `run_batch` and rename module-level functions to private**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/ -m unit` (unchanged — the public API is now `ClaudeRunner.execute(command)` only)
  - Observable: No behaviour change — every existing test continues to pass. After this task, `grep -rn '\.run_batch\(\|\.run_interactive\(\|\.run(' src/i2code/ --include='*.py'` (restricted to `ClaudeRunner` usages) returns zero matches; `grep -rn '^def run_claude_interactive\|^def run_claude_with_output_capture' src/i2code/ --include='*.py'` returns zero matches (only the private `_` variants remain).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/ -m unit` exits 0 and `uvx pyright --level error src/` exits 0 after the deletions.
  - Steps:
    - [ ] Delete `ClaudeRunner.run` at `src/i2code/implement/claude_runner.py:255`
    - [ ] Delete `ClaudeRunner.run_interactive` at `src/i2code/implement/claude_runner.py:261`
    - [ ] Delete `ClaudeRunner.run_batch` at `src/i2code/implement/claude_runner.py:264`
    - [ ] Rename module-level `run_claude_interactive` at `src/i2code/implement/claude_runner.py:42` to `_run_claude_interactive`
    - [ ] Rename module-level `run_claude_with_output_capture` at `src/i2code/implement/claude_runner.py:134` to `_run_claude_with_output_capture`
    - [ ] Update `ClaudeRunner.execute()` internal dispatch to use the new `_run_*` names
    - [ ] Update `tests/implement/fake_claude_runner.py` to remove `run`, `run_interactive`, `run_batch` methods (FakeClaudeRunner now exposes only `execute`)
    - [ ] Update `tests/implement/test_claude_runner.py` to delete the `TestFakeClaudeRunner` tests that exercised `run_interactive`/`run_batch`/`run` (they no longer exist); keep `test_records_execute_call` from Task 2.4
    - [ ] Search for any remaining test imports of `run_claude_interactive` or `run_claude_with_output_capture` and either delete them or update to the private names where the tests legitimately exercise the dispatch layer
    - [ ] Run full unit suite, confirm green

- [ ] **Task 15.2: Remove `build_session_args`, `get_or_create_session_args`, and the public string-returning `read_session_id` aliasing from `session_manager.py`**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/ -m unit`
  - Observable: `grep -rn 'build_session_args\|get_or_create_session_args' src/i2code/ --include='*.py'` returns zero matches. The only public symbols in `src/i2code/session_manager.py` are `read_session_id(path) -> Optional[SessionId]`, `read_or_create_session(path) -> SessionId`, and `create_session_id(path) -> str` (still used internally by `read_or_create_session`).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/ -m unit` exits 0 and `uvx pyright --level error src/` exits 0 after the deletions.
  - Steps:
    - [ ] Delete `build_session_args` at `src/i2code/session_manager.py:23`
    - [ ] Delete `get_or_create_session_args` at `src/i2code/session_manager.py:53`
    - [ ] Confirm `_read_session_id_str` (renamed in Task 3.3) is now unused by external callers; if so, inline it into `read_or_create_session` and delete the helper
    - [ ] Update any tests in `tests/` that exercised the deleted helpers — they should already have been migrated through Steel Threads 3–14; if any remain, delete them
    - [ ] Run full unit suite, confirm green

- [ ] **Task 15.3: Remove `CommandBuilder._with_mode` helper**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -m unit`
  - Observable: `grep -n '_with_mode' src/i2code/implement/command_builder.py` returns zero matches. All `build_*` methods on `CommandBuilder` return `ClaudeCodeCommand` directly without `_with_mode`. No regressions in existing tests.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_command_builder.py -m unit` exits 0 and `uvx pyright --level error src/` exits 0.
  - Steps:
    - [ ] Confirm no `build_*` method still calls `self._with_mode(...)` (search `src/i2code/implement/command_builder.py`)
    - [ ] Delete `_with_mode` at `src/i2code/implement/command_builder.py:30`
    - [ ] Run targeted pytest, confirm green

- [ ] **Task 15.4: End-to-end verification — no raw `["claude"` lists, no old API, full suite green**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `./test-scripts/test-end-to-end.sh` exits 0. `grep -rn '\["claude"' src/i2code/ --include='*.py'` returns exactly ONE match (the canonical `["claude"]` initial list inside `ClaudeRunner._build_argv` in `src/i2code/implement/claude_runner.py`). `grep -rn 'run_batch\|run_interactive\|build_session_args\|get_or_create_session_args' src/i2code/ --include='*.py'` returns zero matches. `command_builder.build_feedback_command` still produces argv containing the 2-token sequence `["--print", "wt-handle-feedback.md"]` (issue #40 preserved). `src/i2code/implement/managed_subprocess.py` is unchanged from `git diff master...HEAD -- src/i2code/implement/managed_subprocess.py`.
  - Evidence: `./test-scripts/test-end-to-end.sh` exits 0; `uvx pyright --level error src/` exits 0; the four `grep` invocations listed above produce the expected match counts.
  - Steps:
    - [ ] Run `./test-scripts/test-end-to-end.sh` and confirm exit 0
    - [ ] Run `uvx pyright --level error src/` and confirm exit 0
    - [ ] Run the four `grep` invocations listed in Observable and confirm match counts
    - [ ] Run `git diff master...HEAD -- src/i2code/implement/managed_subprocess.py` and confirm zero diff
    - [ ] Inspect `command_builder.build_feedback_command`'s test from Task 14.1 to confirm it still asserts the 2-token `--print wt-handle-feedback.md` sequence in the emitted argv
    - [ ] If any check fails, STOP and fix before committing the cleanup

---

## Summary of Migrated Sites (Cross-Reference)

For verification of acceptance criterion §8.2 #7: every site below produces a `ClaudeCodeCommand` and calls `ClaudeRunner.execute(cmd)` by end of Steel Thread 14.

| Site | Migrated in |
|---|---|
| `src/i2code/go_cmd/create_plan.py:22` (batch, allowed_tools, result_text) | ST2 |
| `src/i2code/go_cmd/create_plan.py:70`/`:78` (result_text consumer) | ST2 |
| `src/i2code/design_cmd/create_design.py:64` (interactive, --resume) | ST3 |
| `src/i2code/idea_cmd/brainstorm.py:89` (interactive, --session-id) | ST4 |
| `src/i2code/improve/summary_reports.py:134` (batch, add_dirs) | ST5 |
| `src/i2code/improve/summary_reports.py:145` (result_text consumer) | ST5 |
| `src/i2code/improve/analyze_sessions.py:93` (batch, multi add_dirs) | ST6 |
| `src/i2code/implement/worktree_mode.py:204` (build_task_command) | ST7 |
| `src/i2code/implement/trunk_mode.py:72` (build_task_command) | ST7 |
| `src/i2code/implement/pull_request_review_processor.py:227-230` (triage, mock + non-mock) | ST8 |
| `src/i2code/implement/pull_request_review_processor.py:317-323` (fix, mock + non-mock) | ST9 |
| `src/i2code/implement/pull_request_review_processor.py:457-470` (`_extract_result_text` deletion) | ST8 |
| `src/i2code/implement/commit_recovery.py:48` (build_recovery_command) | ST10 |
| `src/i2code/implement/project_scaffolding.py:35` + `command_builder.py:124-125` (build_scaffolding_command, drops `mock_claude` param) | ST11 |
| `src/i2code/implement/github_actions_build_fixer.py:138-139` (build_ci_fix_command, mock + non-mock) | ST12 |
| `src/i2code/setup_cmd/update_project.py:154` | ST13 |
| `src/i2code/spec_cmd/create_spec.py:42` | ST13 |
| `src/i2code/spec_cmd/revise_spec.py:47` | ST13 |
| `src/i2code/go_cmd/revise_plan.py:36` | ST13 |
| `src/i2code/improve/review_issues.py:117` | ST13 |
| `src/i2code/improve/update_claude_files.py:58` | ST13 |
| `src/i2code/implement/command_builder.py:249` (build_feedback_command, issue #40 preserved via extra_args) | ST14 |
| `src/i2code/implement/claude_runner.py` (old API deletion, module-level rename) | ST15 |
| `src/i2code/session_manager.py` (old helpers deletion) | ST15 |
| `src/i2code/implement/command_builder.py:30` (`_with_mode` deletion) | ST15 |

---

## Change History
### 2026-06-11 17:45 - insert-task-after
Steel Thread 2 currently verifies ClaudeRunner.execute() only with mocked subprocess.Popen (Task 2.3). Adding an integration_claude-marked test that invokes real claude guards against drift between the mocked argv shape and what the real CLI accepts, and confirms that _parse_stream_json_output extracts result_text correctly from real stream-json output (not just synthesized fixtures). Follows the existing pattern in tests/implement/test_triage_real_claude.py.

### 2026-06-11 17:50 - mark-task-complete
Verified baseline: pytest exits 0 (1381 passed, 17 deselected, 4 xfailed); pyright reports 0 errors, 0 warnings, 0 informations

### 2026-06-11 18:11 - mark-task-complete
ClaudeCodeCommand and SessionId dataclasses defined in claude_runner.py with __post_init__ validation; 5 new unit tests pass

### 2026-06-11 18:30 - mark-task-complete
Implemented ClaudeRunner.execute() and _build_argv() helper; targeted pytest green; pyright zero errors; CodeScene safeguard passes.

### 2026-06-11 18:34 - mark-task-complete
Added FakeClaudeRunner.execute(command) with new tests test_records_execute_call and test_execute_returns_configured_result; targeted pytest green.

### 2026-06-16 16:25 - mark-task-complete
ST2 T2.5: create_plan builds ClaudeCodeCommand and reads result_text

### 2026-06-16 16:35 - mark-task-complete
Test test_execute_interactive_no_session locks in the interactive argv contract; _build_argv already appended prompt positionally (no -p, no --verbose, no stream-json) from T2.3 conditional
