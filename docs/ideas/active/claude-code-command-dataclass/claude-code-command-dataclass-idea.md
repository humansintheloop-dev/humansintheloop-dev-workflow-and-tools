# Claude Code Command Dataclass

## Problem

Every site that invokes the Claude Code CLI assembles a raw `List[str]` command line by hand and passes it to a `ClaudeRunner` method. The list-of-strings format leaks Claude Code CLI details (flag names, the `-p` vs interactive convention, `--allowedTools` syntax, `--verbose --output-format=stream-json`) into every caller across the codebase.

Today the pipeline looks like this — caller builds the list, then dispatches:

```python
# src/i2code/go_cmd/create_plan.py:22
cmd = ["claude"]
if repo_root is not None:
    allowed_tools = build_read_only_tools_flag(repo_root)
    cmd += ["--allowedTools", allowed_tools]
cmd += ["-p", rendered_prompt]
return claude_runner.run_batch(cmd, cwd=cwd)
```

```python
# src/i2code/design_cmd/create_design.py:63
session_args = build_session_args(project.session_id_file)
cmd = ["claude"] + session_args + [prompt]
return claude_runner.run_interactive(cmd, cwd=project.directory)
```

```python
# src/i2code/implement/command_builder.py:50
return ["claude"] + extra + [
    "--verbose", "--output-format=stream-json", "-p", prompt
]
```

Consequences:

- **Mode (interactive vs batch) is encoded twice** — once as the presence/absence of `-p` in the list, again as the choice of `run_interactive` vs `run_batch` on the runner. Callers must keep them in sync.
- **CLI-flag knowledge is scattered** across at least 13 construction sites; changes to the Claude CLI (e.g., flag renames, new mandatory options) require touching every one.
- **No type safety** — bugs like the malformed command in `src/i2code/implement/command_builder.py:249` (issue #40) slip past tests that only string-match.
- **Hard to mock the binary path** — the literal string `"claude"` is hardcoded at every site, so swapping in a mock binary for tests requires monkeypatching `subprocess` rather than parameterizing the runner.
- **No central place** to enforce policy (e.g., always include `--verbose --output-format=stream-json` in batch mode so the runner's stream-json parser works).

## Goal

Localize all knowledge of how the `claude` CLI is invoked inside `ClaudeRunner`. Callers describe *what* they want (a prompt, an interaction mode, optional tool permissions, an optional session) via a typed `ClaudeCodeCommand` dataclass. `ClaudeRunner.execute(command)` is the single entry point that translates that description into the actual `argv` and runs it.

Target shape:

```python
@dataclass
class SessionId:
    session_id: str
    is_new: bool   # True → --session-id; False → --resume

@dataclass
class ClaudeCodeCommand:
    cwd: str
    prompt: Optional[str] = None         # required unless mock_command is set
    interactive: Optional[bool] = None   # None = inherit ClaudeRunner default
    allowed_tools: Optional[str] = None  # rendered --allowedTools value
    session_id: Optional[SessionId] = None
    add_dirs: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)
    mock_command: Optional[list[str]] = None  # when set, ClaudeRunner runs this argv as-is

class ClaudeRunner:
    def __init__(self, interactive: bool = True, debug: bool = False): ...
    def execute(self, command: ClaudeCodeCommand) -> ClaudeResult: ...
```

After the change, the example collapses to:

```python
return claude_runner.execute(ClaudeCodeCommand(
    prompt=rendered_prompt,
    cwd=cwd,
    interactive=False,
    allowed_tools=build_read_only_tools_flag(repo_root) if repo_root else None,
))
```

CLI-flag construction (`-p`, `--verbose`, `--output-format=stream-json`, `--resume`, `--session-id`, `--allowedTools`, `--add-dir`, the binary name) lives entirely inside `ClaudeRunner`.

### Behaviour rules for `ClaudeRunner.execute(command)`

1. **Mock short-circuit**: if `command.mock_command is not None`, run it as-is with `cwd=command.cwd`. All other fields are ignored.
2. **Mode resolution**: effective interactive flag is `command.interactive` if not `None`, else `self._interactive` from `__init__`.
3. **Batch policy**: when the effective mode is batch, always prepend `--verbose --output-format=stream-json` and emit the prompt as `-p <prompt>`. Interactive mode passes the prompt positionally.
4. **Session rendering**:
   - `command.session_id is None` → no session flag.
   - `session_id.is_new is True` → `--session-id <session_id.session_id>`.
   - `session_id.is_new is False` → `--resume <session_id.session_id>`.
5. **Allowed tools**: when `command.allowed_tools` is set, append `--allowedTools <value>`.
6. **Add dirs**: each entry in `command.add_dirs` becomes `--add-dir <path>`.
7. **Extra args**: appended verbatim (escape hatch for one-offs like the broken `--print wt-handle-feedback.md` at `command_builder.py:251` — issue #40, intentionally not fixed in this refactor).

### Dispatch

`execute()` dispatches the assembled argv to the existing module-level functions (now private implementation details):
- Interactive → `_run_claude_interactive(argv, cwd)`
- Batch → `_run_claude_with_output_capture(argv, cwd, debug=self._debug)`

### Removed API

- `ClaudeRunner.run`, `run_interactive`, `run_batch` — deleted. `execute()` is the only entry point.
- `src/i2code/session_manager.py`: `build_session_args` and `get_or_create_session_args` (argv-returning helpers) are removed.

### Refactored helpers

`src/i2code/session_manager.py` exposes:
- `read_session_id(path) -> Optional[SessionId]` — for "resume only if present" callers (`design_cmd/create_design.py:63`).
- `read_or_create_session(path) -> SessionId` — for "always have a session" callers (`idea_cmd/brainstorm.py:88`). Returns `is_new=False` when it reads an existing file, `is_new=True` when it generates and writes a new id.

### CommandBuilder migration

`src/i2code/implement/command_builder.py` is kept; each `build_*` method returns a `ClaudeCodeCommand` instead of a `List[str]`. The `_with_mode()` helper disappears (mode resolution moves into `ClaudeRunner`). The mock-binary short-circuit at `build_scaffolding_command` returns a `ClaudeCodeCommand(mock_command=[mock_claude, "setup"])`.

### Caller migration pattern

Every site in the `Locations` section migrates from the "build a list, pick a runner method" pattern to "build a `ClaudeCodeCommand`, call `execute`":

```python
# before:
cmd = ["claude", "--allowedTools", allowed, "-p", prompt]
return claude_runner.run_batch(cmd, cwd=cwd)

# after:
return claude_runner.execute(ClaudeCodeCommand(
    prompt=prompt,
    cwd=cwd,
    interactive=False,
    allowed_tools=allowed,
))
```

Mock-binary short-circuits at `pull_request_review_processor.py:228`/`:318`, `worktree_mode.py:198`, `trunk_mode.py:66`, `github_actions_build_fixer.py:139`, and `command_builder.py:125` translate to `ClaudeCodeCommand(cwd=..., mock_command=[mock_path, label])` — same short-label argv, no prompt rendering, existing mock scripts unchanged.

### Knock-on: batch callers that read stdout as plain text

Always injecting `--verbose --output-format=stream-json` for batch changes observable behaviour at sites that today read `result.output.stdout` as the assistant's reply. Investigation showed only two sites are actually affected:

- `src/i2code/go_cmd/create_plan.py:70` and `:78` (`plan_text = result.output.stdout`).
- `src/i2code/improve/summary_reports.py:145` (`f.write(result.output.stdout)`).

(Other batch sites either don't read stdout or already go through stream-json today.)

**Resolution**: hoist the existing `_extract_result_text` helper from `src/i2code/implement/pull_request_review_processor.py:457-470` into `src/i2code/implement/claude_runner.py`. Call it from `_parse_stream_json_output`. `ClaudeResult` gains a `result_text: str` field populated with the terminal `msg['result']` text (or the raw stdout when not stream-json). The two affected sites switch from `result.output.stdout` to `result.result_text`. `pull_request_review_processor.py` drops its private copy and reads `result.result_text` from the `ClaudeResult` it already gets back. No invented vocabulary — `result` is the protocol's own field name.

## Locations

### Definition (target of the refactor)
- `src/i2code/implement/claude_runner.py:42` — `run_claude_interactive`
- `src/i2code/implement/claude_runner.py:134` — `run_claude_with_output_capture`
- `src/i2code/implement/claude_runner.py:248` — `ClaudeRunner` class with `run` / `run_interactive` / `run_batch`

### Construction sites (callers that build raw `["claude", ...]` lists today)

Interactive:
- `src/i2code/setup_cmd/update_project.py:154`
- `src/i2code/idea_cmd/brainstorm.py:89`
- `src/i2code/design_cmd/create_design.py:64`
- `src/i2code/spec_cmd/create_spec.py:42`
- `src/i2code/spec_cmd/revise_spec.py:47`
- `src/i2code/go_cmd/revise_plan.py:36`
- `src/i2code/improve/review_issues.py:117`
- `src/i2code/improve/update_claude_files.py:58`

Batch (`-p`):
- `src/i2code/go_cmd/create_plan.py:22`
- `src/i2code/improve/analyze_sessions.py:93`
- `src/i2code/improve/summary_reports.py:134`

Builder helpers (also produce raw lists):
- `src/i2code/implement/command_builder.py:48`
- `src/i2code/implement/command_builder.py:50`
- `src/i2code/implement/command_builder.py:134`
- `src/i2code/implement/command_builder.py:136`
- `src/i2code/implement/command_builder.py:249` — currently broken; tracked separately in issue #40

### Supporting helpers that should fold into `ClaudeRunner`
- `src/i2code/session_manager.py:23` — `build_session_args` (`--resume` / `--session-id`)
- `src/i2code/claude/permissions.py:31` — `build_read_only_tools_flag`
- `src/i2code/claude/permissions.py:41` — `build_allowed_tools_flag`

### Unchanged
- `src/i2code/implement/managed_subprocess.py` — process supervision is orthogonal.
- All `subprocess` calls that invoke `git`, `gh`, editors, or `isolarium` — out of scope.
