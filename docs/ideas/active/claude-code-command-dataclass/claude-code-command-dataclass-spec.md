# Platform Capability Specification: Claude Code Command Dataclass

## 1. Purpose and Context

`i2code` invokes the `claude` CLI from many internal call sites. Today each
caller assembles a raw `List[str]` argv (`["claude", ..., "-p", prompt]`)
and chooses one of `ClaudeRunner.run` / `run_interactive` / `run_batch`. This
spreads Claude-CLI knowledge across at least 13 sites (flag names like `-p`,
`--allowedTools`, `--resume`, `--verbose`, `--output-format=stream-json`;
the `claude` binary name itself; the interactive-vs-batch convention).

This capability introduces a typed description of a Claude invocation
(`ClaudeCodeCommand` + `SessionId`) and a single execution entry point
(`ClaudeRunner.execute(command)`). All argv assembly, batch-mode policy,
session-flag rendering, and stream-json result-text extraction live inside
`ClaudeRunner`. Callers describe *what* they want; the runner decides *how*
to invoke `claude`.

The intent and rationale are recorded in
`claude-code-command-dataclass-idea.md`; the design decisions and their
trade-offs are in `claude-code-command-dataclass-discussion.md` (Q1–Q10).

## 2. Consumers

Internal `i2code` modules that today construct `["claude", ...]` argv lists
or call `ClaudeRunner.run*`. Grouped by current invocation pattern:

**Direct argv assembly + `run_batch`:**
- `src/i2code/go_cmd/create_plan.py:22`
- `src/i2code/improve/analyze_sessions.py:93`
- `src/i2code/improve/summary_reports.py:134`

**Direct argv assembly + `run_interactive`:**
- `src/i2code/setup_cmd/update_project.py:154`
- `src/i2code/idea_cmd/brainstorm.py:89`
- `src/i2code/design_cmd/create_design.py:64`
- `src/i2code/spec_cmd/create_spec.py:42`
- `src/i2code/spec_cmd/revise_spec.py:47`
- `src/i2code/go_cmd/revise_plan.py:36`
- `src/i2code/improve/review_issues.py:117`
- `src/i2code/improve/update_claude_files.py:58`

**Via `CommandBuilder` (`src/i2code/implement/command_builder.py`)**, called from:
- `src/i2code/implement/worktree_mode.py:204` (`build_task_command`)
- `src/i2code/implement/trunk_mode.py:72` (`build_task_command`)
- `src/i2code/implement/project_scaffolding.py:35` (`build_scaffolding_command`)
- `src/i2code/implement/commit_recovery.py:48` (`build_recovery_command`)
- `src/i2code/implement/pull_request_review_processor.py:230` (`build_triage_command`)
- `src/i2code/implement/pull_request_review_processor.py:323` (`build_fix_command`)
- `src/i2code/implement/github_actions_build_fixer.py` (`build_ci_fix_command`)

**Mock-binary short-circuits** (today bypass argv assembly entirely):
- `src/i2code/implement/worktree_mode.py:197-198`
- `src/i2code/implement/trunk_mode.py:65-66`
- `src/i2code/implement/pull_request_review_processor.py:227-228` (triage)
- `src/i2code/implement/pull_request_review_processor.py:317-318` (fix)
- `src/i2code/implement/github_actions_build_fixer.py:138-139`
- `src/i2code/implement/command_builder.py:124-125`

There are no external consumers — this is an internal refactor of one
toolchain.

## 3. Capabilities and Behaviours

### 3.1 `SessionId` dataclass

```python
@dataclass(frozen=True)
class SessionId:
    session_id: str
    is_new: bool
```

- `is_new=True` → invocation will use `--session-id <session_id>` (creates a
  new Claude session with this id).
- `is_new=False` → invocation will use `--resume <session_id>` (resumes an
  existing session).

### 3.2 `ClaudeCodeCommand` dataclass

```python
@dataclass
class ClaudeCodeCommand:
    cwd: str
    prompt: Optional[str] = None
    interactive: Optional[bool] = None
    allowed_tools: Optional[str] = None
    session_id: Optional[SessionId] = None
    add_dirs: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)
    mock_command: Optional[list[str]] = None
```

Field semantics:

| Field | Semantics |
|---|---|
| `cwd` | Working directory for the `claude` subprocess. Always required. |
| `prompt` | The rendered prompt text. Required unless `mock_command` is set. |
| `interactive` | `None` ⇒ inherit `ClaudeRunner._interactive`. `True` ⇒ interactive TUI mode. `False` ⇒ batch mode (`-p`). |
| `allowed_tools` | Rendered value passed to `--allowedTools`. Callers produce it via `build_read_only_tools_flag` / `build_allowed_tools_flag` from `src/i2code/claude/permissions.py`. |
| `session_id` | Optional `SessionId`. See 3.1 for flag mapping. |
| `add_dirs` | Each entry becomes one `--add-dir <path>` argument. |
| `extra_args` | Verbatim argv tokens appended after the modeled flags, before the prompt. Used only for one-off flags that don't deserve first-class modeling (e.g., the broken `--print wt-handle-feedback.md` from issue #40). |
| `mock_command` | If set, the runner uses this list as the **complete argv** and ignores all other fields except `cwd`. |

Validation (raised as `ValueError` in `__post_init__` or at `execute()`
entry):
- If `mock_command is None` and `prompt is None` → error.
- Both `mock_command` and `prompt` set is allowed (mock_command wins;
  prompt is ignored). No error.

### 3.3 `ClaudeRunner.execute()` behaviour

```python
class ClaudeRunner:
    def __init__(self, interactive: bool = True, debug: bool = False): ...
    def execute(self, command: ClaudeCodeCommand) -> ClaudeResult: ...
```

`execute()` follows this exact ordered procedure:

1. **Mock short-circuit.** If `command.mock_command is not None`, dispatch
   the argv `command.mock_command` to the existing module-level functions
   (see 3.4) using `cwd=command.cwd` and the runner's default mode
   (`self._interactive`). Return the resulting `ClaudeResult`. Skip all
   subsequent steps.

2. **Resolve mode.** `effective_interactive = command.interactive if
   command.interactive is not None else self._interactive`.

3. **Build argv.** Start with `["claude"]`.

   a. If not `effective_interactive`, append `"--verbose"`,
      `"--output-format=stream-json"`.

   b. If `command.allowed_tools is not None`, append `"--allowedTools"`,
      `command.allowed_tools`.

   c. If `command.session_id is not None`:
      - `session_id.is_new is True` → append `"--session-id"`,
        `session_id.session_id`.
      - `session_id.is_new is False` → append `"--resume"`,
        `session_id.session_id`.

   d. For each `d` in `command.add_dirs`, append `"--add-dir"`, `d`.

   e. Append every token in `command.extra_args` verbatim.

   f. Append the prompt:
      - Interactive: append `command.prompt`.
      - Batch: append `"-p"`, `command.prompt`.

4. **Dispatch.**
   - Interactive: call `_run_claude_interactive(argv, cwd=command.cwd)`.
   - Batch: call `_run_claude_with_output_capture(argv, cwd=command.cwd,
     debug=self._debug)`.

5. **Return** the resulting `ClaudeResult`.

### 3.4 Module-level dispatch functions

The two functions in `src/i2code/implement/claude_runner.py` that today are
public (`run_claude_interactive` at line 42,
`run_claude_with_output_capture` at line 134) are renamed to
`_run_claude_interactive` and `_run_claude_with_output_capture` to mark
them as internal. Their signatures and behaviour are unchanged otherwise.

### 3.5 `ClaudeResult` extension

```python
@dataclass
class ClaudeResult:
    returncode: int
    output: CapturedOutput = field(default_factory=CapturedOutput)
    diagnostics: DiagnosticInfo = field(default_factory=DiagnosticInfo)
    result_text: str = ""
```

`result_text` is populated by `_parse_stream_json_output`:
- If the captured stdout contains stream-json lines and at least one carries
  `type == "result"` with a `result` field, `result_text` is the value of
  `msg["result"]` from that terminal message.
- If no such message is found (e.g., interactive mode, or batch output that
  isn't stream-json for any reason), `result_text` is the captured stdout
  string unchanged. This matches the as-is fallback semantics of the
  existing helper at
  `src/i2code/implement/pull_request_review_processor.py:457-470`.

Interactive `_run_claude_interactive` does not capture stdout (the
subprocess inherits the terminal), so `result_text` is `""` for interactive
results.

### 3.6 Removed APIs

The following are deleted entirely (no deprecation shims):

- `ClaudeRunner.run(cmd, cwd)`
- `ClaudeRunner.run_interactive(cmd, cwd)`
- `ClaudeRunner.run_batch(cmd, cwd)`
- `src/i2code/session_manager.py::build_session_args(path)`
- `src/i2code/session_manager.py::get_or_create_session_args(path)`
- `src/i2code/implement/pull_request_review_processor.py::_extract_result_text`
  (its logic moves into `_parse_stream_json_output`).
- `src/i2code/implement/command_builder.py::_with_mode` helper.
- The `mock_claude` parameter on
  `CommandBuilder.build_scaffolding_command`.

### 3.7 Refactored session helpers

`src/i2code/session_manager.py` exposes:

```python
def read_session_id(path: str) -> Optional[SessionId]:
    """Return SessionId(id, is_new=False) for an existing session-id file,
    or None if the file does not exist."""

def read_or_create_session(path: str) -> SessionId:
    """Return SessionId(id, is_new=False) if the file exists, otherwise
    generate a UUID, write it to `path`, and return SessionId(id, is_new=True)."""
```

The existing `create_session_id(path)` and the private `read_session_id`
file-read helper remain as implementation details.

### 3.8 `CommandBuilder` changes

All `build_*` methods in `src/i2code/implement/command_builder.py` change
signature to return `ClaudeCodeCommand` instead of `List[str]`. Each
method:
1. Renders its existing Jinja template.
2. Constructs a `ClaudeCodeCommand` with:
   - `prompt` = rendered template.
   - `cwd` = the appropriate working directory the caller already provides
     (this means `CommandBuilder` methods gain a `cwd` parameter where they
     don't already take one).
   - `interactive` = the existing interactive flag, mapped to
     `Optional[bool]`.
   - `allowed_tools`, `extra_args`, `add_dirs` populated from existing
     parameters (e.g., `TaskCommandOpts.extra_cli_args` is split: any
     `--allowedTools` value goes to `allowed_tools`; any `--add-dir` value
     goes to `add_dirs`; anything else stays in `extra_args`).
3. The `_with_mode()` helper at line 30 is deleted.

`build_scaffolding_command` loses its `mock_claude` parameter. The mock
short-circuit moves to its caller (`project_scaffolding.py`), which
constructs `ClaudeCodeCommand(cwd=..., mock_command=[mock_claude,
"setup"])` directly when `mock_claude` is set.

`build_feedback_command` is preserved 1:1: it returns
`ClaudeCodeCommand(prompt=prompt, cwd=..., interactive=False,
extra_args=["--print", "wt-handle-feedback.md"])`. Issue #40 (the broken
`--print` argument) is intentionally not fixed by this refactor.

### 3.9 Caller migration

**Non-mock callers**: replace argv assembly with `ClaudeCodeCommand`
construction.

```python
# before — src/i2code/go_cmd/create_plan.py:22
cmd = ["claude"]
if repo_root is not None:
    cmd += ["--allowedTools", build_read_only_tools_flag(repo_root)]
cmd += ["-p", rendered_prompt]
return claude_runner.run_batch(cmd, cwd=cwd)

# after
return claude_runner.execute(ClaudeCodeCommand(
    prompt=rendered_prompt,
    cwd=cwd,
    interactive=False,
    allowed_tools=build_read_only_tools_flag(repo_root) if repo_root else None,
))
```

**Mock callers**: replace short-circuit argv with `mock_command`.

```python
# before — src/i2code/implement/pull_request_review_processor.py:227
if self._opts.mock_claude:
    triage_cmd = [self._opts.mock_claude, f"triage-{pr_number}"]
else:
    triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)
result = self._claude_runner.run_batch(triage_cmd, cwd=...)

# after
if self._opts.mock_claude:
    cmd = ClaudeCodeCommand(
        cwd=self._git_repo.working_tree_dir,
        mock_command=[self._opts.mock_claude, f"triage-{pr_number}"],
    )
else:
    cmd = CommandBuilder().build_triage_command(
        feedback_content, cwd=self._git_repo.working_tree_dir, interactive=False,
    )
result = self._claude_runner.execute(cmd)
```

**Session callers**:

```python
# before — src/i2code/idea_cmd/brainstorm.py:88
session_args = get_or_create_session_args(project.session_id_file)
cmd = ["claude"]
if repo_root is not None:
    cmd += ["--allowedTools", build_allowed_tools_flag(repo_root, project.directory)]
cmd += session_args + [prompt]
return claude_runner.run_interactive(cmd, cwd=cwd)

# after
return claude_runner.execute(ClaudeCodeCommand(
    prompt=prompt,
    cwd=cwd,
    interactive=True,
    allowed_tools=build_allowed_tools_flag(repo_root, project.directory) if repo_root else None,
    session_id=read_or_create_session(project.session_id_file),
))
```

**Callers that consume `result.output.stdout` as text**: switch to
`result.result_text`.

- `src/i2code/go_cmd/create_plan.py:70` and `:78`: `plan_text =
  result.result_text`.
- `src/i2code/improve/summary_reports.py:145`: `f.write(result.result_text)`.
- `src/i2code/implement/pull_request_review_processor.py` (wherever it
  previously called its private `_extract_result_text(...)`): read
  `result.result_text` from the `ClaudeResult` it already gets back.

`src/i2code/improve/analyze_sessions.py` and
`src/i2code/implement/commit_recovery.py:63` do not change their stdout
usage — see Q9 in the discussion-file for the verification.

## 4. APIs, Contracts, Integration Points

### 4.1 Public surface

The following symbols are the public surface of the capability, all in
`src/i2code/implement/claude_runner.py` unless noted:

- `class SessionId`
- `class ClaudeCodeCommand`
- `class ClaudeResult` (extended with `result_text`)
- `class CapturedOutput` (unchanged)
- `class DiagnosticInfo` (unchanged)
- `class ClaudeRunner` with `__init__(interactive: bool = True, debug:
  bool = False)` and `execute(command: ClaudeCodeCommand) -> ClaudeResult`.
- `check_claude_success(exit_code, head_before, head_after)` (unchanged).
- `print_task_failure_diagnostics(claude_result, head_before, head_after)`
  (unchanged).
- `read_session_id(path) -> Optional[SessionId]` and
  `read_or_create_session(path) -> SessionId` in
  `src/i2code/session_manager.py`.

### 4.2 Contract: mock binary

When `mock_command` is set, the runner invokes argv exactly as provided.
Existing test mock scripts that read a short label from `argv[1]` keep
working: callers preserve today's `[mock_path, short_label]` shape (e.g.,
`f"triage-{pr_number}"`, `task_description`, `"setup"`,
`f"fix-{pr_number}-{comment_ids[0]}"`, `f"fix-ci-{run_id}"`). The runner
does not append flags, prompts, or anything else to a `mock_command` argv.

### 4.3 Contract: stream-json result extraction

`result_text` is computed by inspecting captured stdout for stream-json
messages. The algorithm:

1. Split stdout on `\n`. For each non-empty line, attempt `json.loads`.
2. If parsing succeeds and the message has `type == "result"` and a
   `result` key, remember its `result` value.
3. After processing all lines, if any such value was found, `result_text`
   is the *last* such value.
4. Otherwise, `result_text` is the raw captured stdout string.

This matches the as-is semantics of the existing
`_extract_result_text` helper at
`src/i2code/implement/pull_request_review_processor.py:457-470`, which is
deleted from that file as part of this refactor.

## 5. Non-Functional Requirements

| Requirement | Specification |
|---|---|
| **Type safety** | Every Claude invocation flows through `ClaudeCodeCommand` (with `mypy`/`pyright` checking field presence/types) instead of an unstructured `List[str]`. |
| **Locality** | The string `"claude"` appears exactly once in production code (inside `ClaudeRunner.execute`). Test code may reference it as needed. |
| **Diagnostic consistency** | Every batch invocation produces stream-json output, so `DiagnosticInfo.permission_denials`, `error_message`, and `last_messages` are populated meaningfully on every batch result (not just on the CommandBuilder paths). |
| **Behavioural compatibility** | For every call site, the externally observable behaviour after the refactor must match the behaviour before, with one explicit exception: the two sites in §3.9 that switch from `result.output.stdout` to `result.result_text`. The mock-script contract is unchanged. |
| **Performance** | `execute()` adds no measurable overhead over the today's `run*` methods. argv construction is O(N) in the number of fields; subprocess dispatch is identical. |
| **Process supervision** | `src/i2code/implement/managed_subprocess.py` is not modified. |
| **No partial migration** | Old methods (`run`, `run_interactive`, `run_batch`) and old helpers (`build_session_args`, `get_or_create_session_args`) are not retained as wrappers. The refactor lands as a single coherent change. |

## 6. Scenarios and Workflows

### 6.1 Primary end-to-end scenario: plan generation (batch + read-only permissions)

This is the scenario that exercises the largest fraction of the new
capability surface and is the most likely target of a steel-thread plan.

**Setup**: an `IdeaProject` with an idea file and a spec file exists at
`project.directory`. A `ClaudeRunner` and a `repo_root` are available.

**Flow**:

1. Caller renders the `create-implementation-plan.md` template into
   `rendered_prompt`.
2. Caller calls
   ```python
   claude_runner.execute(ClaudeCodeCommand(
       prompt=rendered_prompt,
       cwd=repo_root,
       interactive=False,
       allowed_tools=build_read_only_tools_flag(repo_root),
   ))
   ```
3. `ClaudeRunner.execute()`:
   - `mock_command is None` → skip mock short-circuit.
   - `effective_interactive = False`.
   - Builds argv: `["claude", "--verbose", "--output-format=stream-json",
     "--allowedTools", "Read(/<repo>/**)", "-p", rendered_prompt]`.
   - Calls `_run_claude_with_output_capture(argv, cwd=repo_root,
     debug=False)`.
4. `_parse_stream_json_output` populates
   `DiagnosticInfo.permission_denials` / `error_message` /
   `last_messages` from the stream-json lines, and populates `result_text`
   from the terminal `msg["result"]`.
5. Caller reads `plan_text = result.result_text` and writes it to
   `project.plan_file`.

This scenario verifies: command construction, batch policy auto-injection,
allowed-tools flag rendering, result-text extraction, and one site's
migration from `result.output.stdout` to `result.result_text`.

### 6.2 Secondary scenarios

- **Interactive create_design with --resume**: `ClaudeCodeCommand(prompt,
  cwd=project.directory, interactive=True, session_id=read_session_id(
  project.session_id_file))` → argv `["claude", "--resume", <id>, prompt]`
  if a session file existed; `["claude", prompt]` if it did not.
- **Interactive brainstorm with --session-id (or --resume)**:
  `ClaudeCodeCommand(prompt, cwd=cwd, interactive=True,
  allowed_tools=build_allowed_tools_flag(repo_root, project.directory),
  session_id=read_or_create_session(project.session_id_file))` → argv
  contains `--allowedTools <perms>` and either `--session-id <new_id>` or
  `--resume <id>` depending on whether the session-id file existed.
- **Worktree task execution (mode inherited from runner)**:
  `ClaudeCodeCommand(prompt=task_prompt, cwd=working_tree_dir,
  interactive=None, allowed_tools=...)`. The `ClaudeRunner` is
  instantiated with `interactive=False` for `--non-interactive` runs and
  `interactive=True` otherwise; `execute()` resolves the mode from the
  runner.
- **Mock-binary triage**: `ClaudeCodeCommand(cwd=working_tree_dir,
  mock_command=[mock_path, f"triage-{pr_number}"])`. `execute()`
  short-circuits past argv assembly, runs the mock argv as-is. The mock
  script reads `triage-{pr_number}` from `argv[1]`.
- **summary_reports batch with `--add-dir` and `--allowedTools`**:
  `ClaudeCodeCommand(prompt=rendered, cwd=project_dir, interactive=False,
  allowed_tools="Read", add_dirs=[project_dir])` → argv `["claude",
  "--verbose", "--output-format=stream-json", "--allowedTools", "Read",
  "--add-dir", project_dir, "-p", rendered]`. Caller writes
  `result.result_text` to the report file.
- **analyze_sessions batch with multiple `--add-dir`s**:
  `ClaudeCodeCommand(prompt=rendered, cwd=tracking_dir, interactive=False,
  allowed_tools="Read,Edit,Write", add_dirs=[sessions_dir, issues_dir])`.
  Caller discards `result.result_text` (Claude writes report file
  directly).
- **build_feedback_command (issue #40)**:
  `ClaudeCodeCommand(prompt=rendered, cwd=..., interactive=False,
  extra_args=["--print", "wt-handle-feedback.md"])`. argv (still broken):
  `["claude", "--verbose", "--output-format=stream-json", "--print",
  "wt-handle-feedback.md", "-p", rendered]`. The broken `--print
  <filename>` shape is preserved; fixing it is out of scope.

## 7. Constraints and Assumptions

- **Issue #40 is out of scope.** `build_feedback_command` continues to
  produce a malformed argv via `extra_args`; this refactor preserves the
  bug. A separate task addresses the underlying `--print` misuse.
- **Mock-script contract is preserved.** Existing tests that invoke
  mock scripts with `[mock_path, short_label]` continue to work unchanged.
- **No deprecation period.** The refactor lands as one coherent change
  that removes the old methods and helpers in the same work; downstream
  code is migrated within the same scope.
- **`managed_subprocess.py` is untouched.** Process supervision is
  orthogonal to argv construction.
- **`subprocess` calls for `git`, `gh`, editors, and `isolarium` are out
  of scope.** Only `claude` invocations migrate.
- **The capability is internal.** No CLI flags or `i2code` user-facing
  commands change. No documentation outside the
  `docs/ideas/active/claude-code-command-dataclass/` directory is part of
  the deliverable.
- **`ClaudeRunner` keeps its `Real`/`Mock` shape if test code defines
  variants.** Whatever those variants are, they expose a single
  `execute(command)` method after the refactor.
- **Python type assumptions.** The codebase uses Python 3.10+ syntax for
  type hints (`list[str]`, `Optional[X]`, `tuple[str, bool]`). Dataclasses
  use `field(default_factory=...)` for mutable defaults.

## 8. Acceptance Criteria

A reviewer can declare this capability complete when **all** of the
following hold:

### 8.1 Code structure
1. `src/i2code/implement/claude_runner.py` defines `SessionId`,
   `ClaudeCodeCommand`, and `ClaudeRunner.execute(command)` exactly as
   specified in §3.1, §3.2, and §3.3.
2. `ClaudeRunner` no longer exposes `run`, `run_interactive`, or
   `run_batch`. The module-level `run_claude_interactive` and
   `run_claude_with_output_capture` are renamed to
   `_run_claude_interactive` and `_run_claude_with_output_capture`.
3. `ClaudeResult` has a `result_text: str` field, populated as in §3.5.
4. `_parse_stream_json_output` extracts the terminal `msg["result"]`
   value into `result_text`, falling back to raw stdout when no
   stream-json `result` message is present.
5. `src/i2code/session_manager.py` exposes `read_session_id(path) ->
   Optional[SessionId]` and `read_or_create_session(path) -> SessionId`,
   and no longer exposes `build_session_args` or
   `get_or_create_session_args`.
6. `src/i2code/implement/command_builder.py`'s `build_*` methods all
   return `ClaudeCodeCommand`. The `_with_mode` helper is removed. The
   `mock_claude` parameter is removed from `build_scaffolding_command`.

### 8.2 Caller migration
7. Every call site listed in §2 has been migrated to call
   `claude_runner.execute(ClaudeCodeCommand(...))`. A grep for
   `\["claude"` in `src/i2code/` returns zero matches (the literal lives
   only inside `_build_argv` / `execute` in `claude_runner.py`).
8. A grep for `run_batch\|run_interactive\|\.run\(` against
   `ClaudeRunner` usages in `src/i2code/` returns zero matches.
9. A grep for `build_session_args\|get_or_create_session_args` returns
   zero matches.
10. `src/i2code/go_cmd/create_plan.py:70`/`:78` and
    `src/i2code/improve/summary_reports.py:145` read `result.result_text`
    (not `result.output.stdout`).
11. `_extract_result_text` is removed from
    `src/i2code/implement/pull_request_review_processor.py`; the file
    reads `result.result_text` from the `ClaudeResult` it already
    receives.
12. Every mock-binary short-circuit listed in §2 constructs a
    `ClaudeCodeCommand` with `mock_command=[mock_path, short_label]`
    where `short_label` matches today's value verbatim.

### 8.3 Behaviour
13. For every call site (other than the two explicitly migrated stdout
    consumers), the argv emitted to `subprocess` after the refactor
    matches the argv emitted before the refactor, modulo
    `--verbose --output-format=stream-json` being added to the three batch
    sites at `create_plan.py:22`, `analyze_sessions.py:93`, and
    `summary_reports.py:134` (and only there).
14. Existing test suites pass without modification of test-side mock
    scripts. (Test code that called `run_batch` / `run_interactive`
    directly is updated to use `execute`.)
15. `pyright --level error src/` reports zero new errors introduced by
    the refactor.

### 8.4 Out-of-scope confirmation
16. `command_builder.build_feedback_command` still produces argv that
    contains `--print wt-handle-feedback.md` as a 2-token sequence
    (i.e., issue #40 remains broken in the same shape).
17. `src/i2code/implement/managed_subprocess.py` is unchanged.
18. No `subprocess` invocation of `git`, `gh`, editors, or `isolarium` is
    modified.
