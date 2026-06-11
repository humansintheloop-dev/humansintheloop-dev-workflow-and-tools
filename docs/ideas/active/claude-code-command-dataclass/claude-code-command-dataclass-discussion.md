# Discussion: Claude Code Command Dataclass

## Classification

**Type C — Platform / infrastructure capability.**

Rationale: This refactor consolidates how the `claude` CLI is invoked inside
the `i2code` toolchain. It introduces a new internal abstraction
(`ClaudeCodeCommand` dataclass + `ClaudeRunner.execute(command)`) so that
callers stop assembling `List[str]` argv lists by hand. The change is not
user-visible (no new command or flag for end users), it is not validating an
architectural concern (e.g., performance, integration risk), and it is not an
example/teaching repo. It is an internal capability that the rest of the
codebase consumes — i.e., a platform/infrastructure capability.

## Codebase context gathered before asking questions

- `src/i2code/implement/claude_runner.py` — `ClaudeRunner` exposes `run`,
  `run_interactive`, `run_batch`, all taking `cmd: List[str]` + `cwd`.
  Module-level functions `run_claude_interactive` and
  `run_claude_with_output_capture` do the actual `subprocess` work.
- `src/i2code/implement/command_builder.py` — `CommandBuilder` builds raw
  `["claude", ...]` lists for several flows (task, scaffolding, recovery,
  triage, fix, ci-fix, feedback). It encodes the `interactive`-vs-`-p` split
  via a `_with_mode()` helper.
- `src/i2code/session_manager.py` — `build_session_args` and
  `get_or_create_session_args` translate a session-id file into either
  `["--resume", id]` or `["--session-id", new_id]`.
- `src/i2code/claude/permissions.py` — `build_read_only_tools_flag` and
  `build_allowed_tools_flag` return the rendered `--allowedTools` value
  (caller is responsible for prepending `--allowedTools`).
  `calculate_claude_permissions` returns a `List[str]` used to assemble the
  flag in `worktree_mode.py:202`.
- Construction sites that assemble `["claude", ...]` directly:
  `go_cmd/create_plan.py:22`, `go_cmd/revise_plan.py:36`,
  `setup_cmd/update_project.py:154`, `idea_cmd/brainstorm.py:89`,
  `design_cmd/create_design.py:64`, `spec_cmd/create_spec.py:42`,
  `spec_cmd/revise_spec.py:47`, `improve/review_issues.py:117`,
  `improve/update_claude_files.py:58`, `improve/analyze_sessions.py:93`,
  `improve/summary_reports.py:134`, plus the `command_builder.py` helpers.
- Run-callers of `ClaudeRunner`: `worktree_mode.py`, `trunk_mode.py`,
  `project_scaffolding.py`, `commit_recovery.py`, `pull_request_review_processor.py`,
  `github_actions_build_fixer.py`.
- Mock-binary handling today: `worktree_mode.py:198` and
  `command_builder.py:124` short-circuit to a custom argv list when
  `mock_claude` is set, rather than overriding the `"claude"` binary.
- Special-shape command not covered by the sketched dataclass:
  `command_builder.py:249` builds `["claude", "--print",
  "wt-handle-feedback.md", "-p", prompt]` (this is the broken command
  tracked by issue #40).

## Questions & answers

### Q1. How structured should `ClaudeCodeCommand` fields be — intent or rendered CLI strings?

Options considered:
- **Rendered strings** (matches the sketch): `allowed_tools` is the already-rendered `--allowedTools` value, `session_id` is a bare UUID, etc. Callers keep calling `build_read_only_tools_flag()` and `read_session_id()` to produce those values.
- **Intent fields**: `permissions=Permissions.read_only(repo_root)`, `session=SessionFromFile(path)`. ClaudeRunner owns rendering and any file I/O.
- **Mixed**: intent fields for recurring concerns; `extra_args` escape hatch for one-offs.

**Answer:** Rendered strings (Option 1).

Implications:
- The dataclass shape matches the sketch in the idea-file.
- Helpers in `src/i2code/claude/permissions.py` (`build_read_only_tools_flag`,
  `build_allowed_tools_flag`) stay where they are; callers still invoke them
  and pass the resulting string into `allowed_tools`.
- `src/i2code/session_manager.py` (`read_session_id`,
  `get_or_create_session_args`, `build_session_args`) stays where it is, but
  the *flag wrapping* (`--resume`, `--session-id`) moves into `ClaudeRunner` —
  callers will pass the bare id via `session_id` / `new_session_id` instead of
  pre-rendered `["--resume", id]` lists.
- `ClaudeRunner` is responsible for the **flag names** (`-p`, `--verbose`,
  `--output-format=stream-json`, `--allowedTools`, `--resume`, `--session-id`,
  `--add-dir`, and the `claude` binary itself); callers are responsible for
  the **flag values** (the permission grammar, the actual UUIDs).

### Q2. Where does the interactive-vs-batch mode get decided?

Options considered:
- **Command only**: drop `ClaudeRunner.__init__(interactive=...)`; every command
  must set `interactive` explicitly.
- **Runner default + command override**: keep `ClaudeRunner(interactive=...)`
  as the default; `ClaudeCodeCommand.interactive: Optional[bool] = None` means
  "inherit runner default", non-None overrides.
- **Runner only**: mode lives only on `ClaudeRunner`; no `interactive` field
  on the command at all.

**Answer:** Runner default + command override (matches the sketch).

Implications:
- `ClaudeRunner.__init__` keeps its `interactive: bool = True` argument.
- `ClaudeCodeCommand.interactive: Optional[bool] = None`. Inside
  `ClaudeRunner.execute`, the effective mode is
  `command.interactive if command.interactive is not None else self._interactive`.
- Call sites that always want batch (`go_cmd/create_plan.py`,
  `improve/analyze_sessions.py`, `improve/summary_reports.py`,
  `commit_recovery.py`, `pull_request_review_processor.py` triage) set
  `interactive=False` on the command.
- Call sites that always want interactive (`design_cmd`, `spec_cmd`,
  `idea_cmd`, `setup_cmd/update_project`, `improve/review_issues`,
  `improve/update_claude_files`, `go_cmd/revise_plan`) set
  `interactive=True` on the command.
- Call sites that follow a runtime mode (`worktree_mode`, `trunk_mode`,
  `project_scaffolding` — driven by `--non-interactive` opt or
  `mock_claude`) leave `command.interactive = None` and rely on the
  `ClaudeRunner` they were constructed with.

### Q3. End state for the existing `ClaudeRunner` methods (`run`, `run_interactive`, `run_batch`)?

Options considered:
- **Remove entirely** once every caller migrates.
- **Keep as thin wrappers** that build a `ClaudeCodeCommand` internally.
- **Deprecate then delete** in a follow-up task.

**Answer:** Remove entirely. `ClaudeRunner.execute(ClaudeCodeCommand)` is the
only entry point at the end of the refactor.

Implications:
- Every caller listed in the idea-file `Locations` section migrates to
  `execute()` within this work.
- The module-level `run_claude_interactive` and
  `run_claude_with_output_capture` functions stay (they hold the actual
  `subprocess` logic) but become private implementation details that
  `execute()` dispatches to based on the resolved `interactive` flag.
- `Mock`/`Real` `ClaudeRunner` variants (if any in tests) gain a single
  `execute` method to override.
- The PR/refactor must touch every site in one go (no two-step migration).

### Q4. What happens to `CommandBuilder`?

Options considered:
- **Returns `ClaudeCodeCommand`**: keep the class and each `build_*` method,
  but change the return type from `List[str]` to `ClaudeCodeCommand`.
- **Becomes `PromptBuilder`**: reduced to template rendering returning a
  prompt string; callers build the `ClaudeCodeCommand`.
- **Dissolve**: remove the class; callers render templates and construct
  `ClaudeCodeCommand` inline.

**Answer:** `CommandBuilder` stays; its methods return `ClaudeCodeCommand`.

Implications:
- All `CommandBuilder.build_*` methods change signature to return
  `ClaudeCodeCommand` instead of `List[str]`.
- The `_with_mode()` helper in `command_builder.py:30` disappears — mode
  resolution moves to `ClaudeRunner`.
- The mock-binary short-circuit at `command_builder.py:124` for
  `build_scaffolding_command` (returning `[mock_claude, "setup"]` directly)
  needs another expression; covered by the still-open mock-binary question.
- The special-shape command at `command_builder.py:249` (`["claude",
  "--print", "wt-handle-feedback.md", "-p", prompt]`) also needs to fit the
  dataclass; covered later (relates to issue #40 and `extra_args`).
- Callers (`worktree_mode.py`, `trunk_mode.py`,
  `pull_request_review_processor.py`, `project_scaffolding.py`,
  `commit_recovery.py`, `github_actions_build_fixer.py`) all become
  `runner.execute(builder.build_X(...))`.

### Q5. How does the mock-binary path work?

Background: today, several sites short-circuit normal command construction when `mock_claude` is set, returning a hand-built argv `[mock_path, short_label]` where the label is a small identifier the mock script reads off `argv[1]` (not the full rendered prompt). Examples:

- `src/i2code/implement/pull_request_review_processor.py:228` — `[mock_claude, f"triage-{pr_number}"]`
- `src/i2code/implement/pull_request_review_processor.py:318` — `[mock_claude, f"fix-{pr_number}-{comment_ids[0]}"]`
- `src/i2code/implement/worktree_mode.py:198` — `[mock_claude, task_description]`
- `src/i2code/implement/trunk_mode.py:66` — `[mock_claude, task_description]`
- `src/i2code/implement/github_actions_build_fixer.py:139` — `[mock_claude, f"fix-ci-{run_id}"]`
- `src/i2code/implement/command_builder.py:125` — `[mock_claude, "setup"]`

**Answer:** `ClaudeCodeCommand` gets an optional `mock_command: Optional[list[str]] = None` field that holds the **complete argv** to run.

Semantics inside `ClaudeRunner.execute(command)`:
- If `command.mock_command is not None`: run it exactly as-is. All other fields (`prompt`, `interactive`, `allowed_tools`, session ids, `add_dirs`, `extra_args`) are ignored.
- Otherwise: assemble argv from `prompt` + flags as usual.

Implications:
- Every short-circuit site stops returning a raw `List[str]` and instead returns a `ClaudeCodeCommand(cwd=..., mock_command=[mock_path, label])`.
- `CommandBuilder.build_scaffolding_command` no longer takes a `mock_claude` parameter; the caller (`project_scaffolding.py`) constructs the mock command inline.
- The short-label semantics (mock script reads a small identifier off `argv[1]`) are preserved unchanged — existing test mock scripts keep working.
- `prompt` becomes `Optional[str]` on the dataclass (since `mock_command`-only invocations don't need it), or remains required and is set to `""` for mock paths. (Choice deferred to spec.)

### Q6. Should `ClaudeRunner.execute()` always inject `--verbose --output-format=stream-json` for batch commands?

Background: today only `command_builder.py:51` and `:140` include these flags. `go_cmd/create_plan.py:22`, `improve/analyze_sessions.py`, `improve/summary_reports.py`, and `commit_recovery.py` go through `run_batch` → `run_claude_with_output_capture`, which calls `_parse_stream_json_output` on stdout that isn't stream-json — silently producing empty `DiagnosticInfo`.

**Answer:** Always inject. When the resolved mode is batch, `execute()` prepends `--verbose --output-format=stream-json` and emits the prompt as `-p <prompt>`.

Implications:
- Consistent diagnostics on every batch invocation.
- **Side effect to address**: the four sites that currently treat `result.output.stdout` as plain assistant text — `go_cmd/create_plan.py:70` (`plan_text = result.output.stdout`), `improve/analyze_sessions.py`, `improve/summary_reports.py`, `commit_recovery.py` — would now see stream-json messages on stdout. These callers must change to read the assistant text from a parsed source.
- Follow-up needed: should `ClaudeResult` be extended with a parsed `assistant_text` field (computed by `_parse_stream_json_output`) so callers don't each re-parse? Deferred to spec.

### Q7. Is fixing issue #40 (broken command at `command_builder.py:249-253`) in scope?

Options considered:
- **Out of scope**: port the broken command shape 1:1 into a `ClaudeCodeCommand` (via `extra_args`); leave #40 for separate work.
- **In scope**: investigate intent and emit the correct command.
- **Delete the call site**: remove `build_feedback_command` if unreachable.

**Answer:** Out of scope. The refactor preserves current behaviour byte-for-byte. `build_feedback_command` returns a `ClaudeCodeCommand` whose `extra_args` carries `["--print", "wt-handle-feedback.md"]`. The flag is still broken; this refactor doesn't address that.

Implications:
- `ClaudeCodeCommand.extra_args: list[str]` (sketched in idea-file) is needed at minimum to carry this one edge case.
- Issue #40 remains open for separate work.

### Q8. How do callers populate `session_id` / `new_session_id`?

Background: today `design_cmd/create_design.py:63` uses `build_session_args(path)` returning `["--resume", id]` or `[]`; `idea_cmd/brainstorm.py:88` uses `get_or_create_session_args(path)` returning `["--resume", id]` or `["--session-id", new_id]`.

**Answer:** A single `session_id: Optional[SessionId] = None` field on `ClaudeCodeCommand`, where `SessionId` is a small dataclass carrying both the id and an `is_new` discriminator. `ClaudeRunner.execute()` inspects `is_new` to decide which flag to emit.

```python
@dataclass
class SessionId:
    session_id: str
    is_new: bool

@dataclass
class ClaudeCodeCommand:
    ...
    session_id: Optional[SessionId] = None
```

Inside `ClaudeRunner.execute()`:
- `command.session_id is None` → no session flag.
- `command.session_id.is_new is True` → `--session-id <session_id>`.
- `command.session_id.is_new is False` → `--resume <session_id>`.

Helpers in `src/i2code/session_manager.py` are refactored to return `SessionId` directly:
- `read_or_create_session(path) -> SessionId` — "always have a session" (brainstorm). Reads existing file (`is_new=False`) or creates one and writes it (`is_new=True`).
- `read_session_id(path) -> Optional[SessionId]` — "resume only if present" (create_design). Returns `None` if no file.

Old helpers `build_session_args` and `get_or_create_session_args` are removed (they returned argv lists, no longer needed once `--resume`/`--session-id` rendering moves into `ClaudeRunner.execute`).

Call sites become:
```python
# idea_cmd/brainstorm.py:88
cmd = ClaudeCodeCommand(
    ...,
    session_id=read_or_create_session(project.session_id_file),
)

# design_cmd/create_design.py:63
cmd = ClaudeCodeCommand(
    ...,
    session_id=read_session_id(project.session_id_file),
)
```

This drops the awkward two-parallel-field shape from the original sketch (`session_id` + `new_session_id`) in favour of one optional discriminated value — slight deviation from Q1's "rendered strings" stance, but localised and removes a foot-gun (both fields set simultaneously).

### Q9. How should the Q6 behaviour change be addressed?

Investigation finding: only **two** sites actually consume `result.output.stdout` as plain text — not four as initially claimed.

- `src/i2code/improve/analyze_sessions.py` — does not read stdout. The template gives Claude `Edit,Write` tools to write the report file directly; the returned `ClaudeResult` is discarded by `cli.py:24`.
- `src/i2code/implement/commit_recovery.py:63` — does `"<SUCCESS>" in claude_result.output.stdout`, but it already goes through `CommandBuilder.build_recovery_command` → `_with_mode` which already adds stream-json today. The substring check works because the marker is embedded in the result message's text content. No change.
- `src/i2code/improve/summary_reports.py:145` — `f.write(result.output.stdout)`. **Real behaviour change.**
- `src/i2code/go_cmd/create_plan.py:70` and `:78` — `plan_text = result.output.stdout`. **Real behaviour change.**

A helper already exists for the conversion: `pull_request_review_processor.py:457-470` (`_extract_result_text`) — extracts `msg['result']` from a terminal `result`-typed stream-json message, or returns the input as-is if not stream-json.

**Answer:** Hoist `_extract_result_text` into `claude_runner.py`. Call it from `_parse_stream_json_output`. `ClaudeResult` gains a `result_text: str` field. The two affected sites switch from `result.output.stdout` to `result.result_text`.

Implications:
- `pull_request_review_processor.py:459` — `_extract_result_text` is removed from that file and replaced with a read of `result.result_text` from the `ClaudeResult` it already gets back.
- `_parse_stream_json_output` is the single place that knows the stream-json schema.
- The field name `result_text` reuses the protocol's own term (`msg['result']`); no invented vocabulary.
- Q6 stands: stream-json is always injected for batch.

### Q10. Any additional requirements or concerns before moving to the specification step?

**Answer:** No — done.
