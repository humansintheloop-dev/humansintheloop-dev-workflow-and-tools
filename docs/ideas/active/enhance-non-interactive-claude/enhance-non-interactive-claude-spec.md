# Platform Capability Specification: Enhance Non-Interactive Claude

## Purpose and Context

Non-interactive Claude invocations (`run_batch()`) are the backbone of all automated workflows in i2code — task execution, commit recovery, scaffolding, PR triage, PR fixes, plan generation, and session analysis. Currently, these invocations suffer from three problems:

1. **Inconsistent prompt construction** — SUCCESS/FAILURE/NOTHING-TO-DO tag instructions are duplicated across templates. Some include them, some don't.
2. **Scattered result checking** — Each caller implements its own ad-hoc pattern for detecting success/failure (string search for tags, exit code checks, HEAD advancement). The `<FAILURE>` tag is defined in prompts but never parsed.
3. **Opaque progress** — Users see only a stream of dots with no indication of what Claude is doing.

### Current Architecture

The platform layer consists of:

- **`claude_runner.py`** — `ClaudeRunner` class with `run_batch()` method delegating to `run_claude_with_output_capture()`. Returns `ClaudeResult` dataclass (returncode, output, diagnostics). No custom exceptions.
- **`command_builder.py`** — Constructs CLI commands using Jinja2 templates. Non-interactive mode adds `--verbose --output-format=stream-json -p`.
- **Progress display** — `_print_dot_per_line()` prints one dot per JSON line to stdout.
- **Diagnostics** — `_parse_stream_json_output()` extracts permission denials, error messages, and last 5 messages from stream-json output.
- **`check_claude_success()`** — Checks exit code AND HEAD advancement. Conflates platform concern (exit code) with caller concern (commits).
- **`print_task_failure_diagnostics()`** — Prints exit code, HEAD before/after, permission denials, error messages, and last messages. Mixes platform diagnostics with caller-specific HEAD context.

---

## Consumers

All modules that invoke `run_batch()` on `ClaudeRunner`:

| Consumer | File | Invocation | Current Result Handling |
|----------|------|------------|------------------------|
| trunk_mode | `trunk_mode.py` | `run()` → `run_batch()` | `check_claude_success()` + `<SUCCESS>` string search. Retry loop with `continue` / `sys.exit(1)` |
| worktree_mode | `worktree_mode.py` | `run()` → `run_batch()` | Same as trunk_mode |
| commit_recovery | `commit_recovery.py` | `run_batch()` direct | `check_claude_success()` + `<SUCCESS>` string search. Returns `False` on failure, caller retries up to 2x |
| project_scaffolding | `project_scaffolding.py` | `run()` → `run_batch()` | `<SUCCESS>` or `<NOTHING-TO-DO>` string search |
| PR triage | `pull_request_review_processor.py` | `run_batch()` direct | JSON parsing (no tags) |
| PR fix | `pull_request_review_processor.py` | `run_batch()` direct | HEAD advancement check |
| create_plan | `create_plan.py` | `run_batch()` direct | Plan text in stdout |
| summary_reports | `summary_reports.py` | `run_batch()` direct | stdout written to file |
| analyze_sessions | `analyze_sessions.py` | `run_batch()` direct | Returns ClaudeResult directly |

---

## Capabilities and Behaviors

### Capability 1: Auto-Inject Outcome Tag Instructions

`run_batch()` automatically appends a standard prompt block instructing Claude to wrap its final output in `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>` tags.

**Behavior:**

- The outcome tag instructions are rendered from a Jinja2 template (e.g., `outcome_tags.j2`), parameterized by the template's front-matter.
- Before appending, `run_batch()` checks if the prompt already contains `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>` strings. If present, injection is skipped (the template owns the tags).
- If injection proceeds, `run_batch()` parses optional YAML front-matter from the prompt (see below), strips the front-matter from the prompt, and renders the outcome tag template using the extracted parameters.
- The injected instructions tell Claude:
  - Wrap final output in `<SUCCESS>...</SUCCESS>` on success. The payload description comes from front-matter if present, otherwise uses the generic default "describe what you did".
  - Wrap final output in `<FAILURE>...</FAILURE>` on failure, with an explanation.
  - Wrap final output in `<NOTHING-TO-DO>...</NOTHING-TO-DO>` if no action was needed — **only if `nothing_to_do` is declared in front-matter**.
  - Emit `<INFO>...</INFO>` messages periodically during work to indicate progress. Claude decides granularity.

**YAML front-matter:**

Templates can include optional YAML front-matter (Jekyll-style) to parameterize the outcome tag instructions:

```yaml
---
outcome:
  success: "the commit SHA in format: task implemented: COMMIT_SHA"
  nothing_to_do: "explanation of why no changes were needed"
---
```

Front-matter fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `outcome.success` | No | Generic "describe what you did" | Payload description for `<SUCCESS>` tag |
| `outcome.failure` | No | "explain what went wrong" | Payload description for `<FAILURE>` tag |
| `outcome.nothing_to_do` | No | *omitted* | If present, `<NOTHING-TO-DO>` tag is included in instructions with this description. If absent, no `<NOTHING-TO-DO>` instruction is injected. |

**Three-tier resolution:**

1. **Tags already in prompt** → skip injection entirely (template owns the tags).
2. **Front-matter present** → parse parameters, strip front-matter from prompt, render outcome template with parameters.
3. **No front-matter, no tags** → render outcome template with generic defaults (SUCCESS + FAILURE only, no NOTHING-TO-DO).

**Separation of concerns:**

- **Templates** declare *what the payload should contain* via front-matter — e.g., "output the commit SHA", "output JSON with will_fix and needs_clarification".
- **Platform** (`run_batch()`) defines the *envelope* — the tags themselves and the standard instructions around them.
- Templates that need full control over tag instructions can include them directly in the template body (skipping injection via tier 1).

**Template changes required:**

| Template | Current State | Action |
|----------|--------------|--------|
| `task_execution.j2` | SUCCESS/FAILURE tags (unconditional) | Remove tag instructions, add front-matter with `success: "task implemented: COMMIT_SHA"` |
| `commit_recovery.j2` | SUCCESS/FAILURE tags (unconditional) | Remove tag instructions, add front-matter with `success: "recovery commit: COMMIT_SHA"` |
| `scaffolding.j2` | SUCCESS/FAILURE/NOTHING-TO-DO tags | Remove tag instructions, add front-matter with `success: "Scaffold created: COMMIT_SHA"` and `nothing_to_do: "No changes needed"` |
| `triage_feedback.j2` | No tags (JSON-based) | Add front-matter with `success: "the triage JSON"` |
| `fix_feedback.j2` | No tags | Add front-matter with `success: "fix applied: COMMIT_SHA"` |
| `ci_fix.j2` | No tags | Add front-matter with `success: "CI fix applied: COMMIT_SHA"` |

### Capability 2: Centralized Result Parsing with Exceptions

After process completion, `run_batch()` parses the outcome from full stdout and either returns a result or raises an exception.

**Success outcomes (return):**

- `SUCCESS` or `NOTHING_TO_DO` — returns enhanced `ClaudeResult` with:
  - `outcome`: enum value (`ClaudeOutcome.SUCCESS` or `ClaudeOutcome.NOTHING_TO_DO`)
  - `payload`: string content extracted from inside the outcome tag
  - Existing fields preserved: `returncode`, `output`, `diagnostics`

**Failure outcomes (raise):**

Platform diagnostics are printed to stderr before raising. Caller-specific context (HEAD before/after, attempt count) stays with callers.

**Exception hierarchy:**

```
ClaudeRetryableError          ← catch to retry
├── ClaudeProcessError        ← non-zero exit code (crash, timeout)
└── ClaudeInterrupted         ← returncode 130 (CTRL-C / SIGTERM)

ClaudeFailure                 ← catch to fail fast
└── ClaudeMissingOutcomeTag   ← exit 0 but no outcome tag found
```

**Exception classification logic in `run_batch()`:**

1. If returncode is 130 → raise `ClaudeInterrupted`
2. If returncode is non-zero → raise `ClaudeProcessError`
3. If returncode is 0 and `<FAILURE>` tag found → raise `ClaudeFailure` with payload
4. If returncode is 0 and no outcome tag found → raise `ClaudeMissingOutcomeTag`
5. If returncode is 0 and `<SUCCESS>` or `<NOTHING-TO-DO>` found → return `ClaudeResult` with outcome and payload

**All exceptions carry:**
- `claude_result`: the full `ClaudeResult` (exit code, output, diagnostics)
- `payload`: string content from the tag (for `ClaudeFailure`; `None` for process errors)

**Caller migration patterns:**

| Consumer | Current Pattern | New Pattern |
|----------|----------------|-------------|
| trunk_mode / worktree_mode | `check_claude_success()` + string search + `continue`/`sys.exit(1)` | `try/except ClaudeRetryableError: continue` + `except ClaudeFailure: sys.exit(1)` |
| commit_recovery | `check_claude_success()` + string search + `return False` | `try/except ClaudeRetryableError: return False` |
| scaffolding | String search for tags | Check `result.outcome` enum |
| PR triage | JSON parsing of stdout | Parse JSON from `result.payload` |
| PR fix | HEAD check | `try/except` + caller HEAD check |
| create_plan, summary_reports, analyze_sessions | Use stdout directly | `try/except` for error handling; access stdout as before |

### Capability 3: Streaming INFO Messages

The streaming line processor detects `<INFO>` tags during execution and displays them inline with progress dots.

**Detection:**

- INFO tags are detected in the streaming line processor (same place dots are printed).
- Each stream-json line is a complete JSON object. INFO tags will not span line boundaries.
- Detection uses raw string scan on each stream-json line.

**Display format:**

```
.......
  Reading source files
.........
  Running tests
....
  Committing changes
...
```

- Dots remain as baseline progress indicator.
- When an `<INFO>` tag is detected: print newline, print the INFO message (indented), resume dots on the next line.
- Preserves history (scrollable), works in CI/non-TTY environments.

### Capability 4: Refactored Diagnostics

**`print_task_failure_diagnostics()` changes:**

- Remove `head_before` and `head_after` parameters.
- Print platform diagnostics only: exit code, permission denials, error messages, last messages.
- Called by `run_batch()` internally before raising exceptions.

**`check_claude_success()` disposition:**

- Remove from `claude_runner.py`. Callers that need HEAD checking implement it themselves.
- HEAD advancement is a caller concern — not all callers expect a commit (e.g., PR triage, plan generation, summary reports).
- Callers that care about commits check HEAD themselves.

---

## High-Level APIs and Contracts

### `ClaudeRunner.run_batch(cmd, cwd) -> ClaudeResult`

**Contract:**

- **Input:** CLI command list and working directory.
- **Pre-processing:**
  1. Extract the prompt (last element of cmd after `-p`).
  2. If the prompt contains `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>` → skip injection.
  3. Otherwise, parse optional YAML front-matter from the prompt. Strip front-matter from the prompt.
  4. Render outcome tag instructions from `outcome_tags.j2` using front-matter parameters (or generic defaults).
  5. Append the rendered instructions to the prompt.
- **Execution:** Run subprocess, stream dots + INFO messages.
- **Post-processing:** Parse outcome tags from full stdout.
- **Returns:** `ClaudeResult` with `outcome` and `payload` on success.
- **Raises:** `ClaudeRetryableError` or `ClaudeFailure` on failure, after printing platform diagnostics.

### `ClaudeResult` (enhanced)

```python
@dataclass
class ClaudeResult:
    returncode: int
    output: CapturedOutput
    diagnostics: DiagnosticInfo
    outcome: ClaudeOutcome      # NEW: SUCCESS or NOTHING_TO_DO
    payload: str                # NEW: content from inside the outcome tag
```

### `ClaudeOutcome` (new enum)

```python
class ClaudeOutcome(Enum):
    SUCCESS = "SUCCESS"
    NOTHING_TO_DO = "NOTHING_TO_DO"
```

### Exception classes (new)

```python
class ClaudeRetryableError(Exception):
    def __init__(self, claude_result: ClaudeResult): ...

class ClaudeProcessError(ClaudeRetryableError): ...

class ClaudeInterrupted(ClaudeRetryableError): ...

class ClaudeFailure(Exception):
    def __init__(self, claude_result: ClaudeResult, payload: str | None): ...

class ClaudeMissingOutcomeTag(ClaudeFailure): ...
```

### Auto-injection template (new)

A Jinja2 template (e.g., `outcome_tags.j2`) containing the standard instructions for outcome tags and INFO messages. Rendered by `run_batch()` and appended to the prompt when tags are not already present.

**Template variables:**

- `success_payload`: string — description of what to put inside `<SUCCESS>` (default: "describe what you did")
- `failure_payload`: string — description of what to put inside `<FAILURE>` (default: "explain what went wrong")
- `include_nothing_to_do`: bool — whether to include `<NOTHING-TO-DO>` instructions
- `nothing_to_do_payload`: string — description of what to put inside `<NOTHING-TO-DO>` (only used when `include_nothing_to_do` is true)

---

## Non-Functional Requirements

### Backward Compatibility

- Existing `ClaudeResult` fields (`returncode`, `output`, `diagnostics`) remain unchanged.
- Callers that currently ignore tags and use stdout directly (create_plan, summary_reports, analyze_sessions) continue to work — they catch exceptions for error handling and access `output.stdout` as before.
- The `outcome` and `payload` fields are additions, not replacements.

### Observability

- INFO messages provide real-time progress visibility during long-running invocations.
- Platform diagnostics (permission denials, error messages, last messages) are printed to stderr before exceptions are raised.

### Reliability

- Exception hierarchy enables callers to implement retry logic cleanly: catch `ClaudeRetryableError` to retry, let `ClaudeFailure` propagate.
- Signal handling (CTRL-C / SIGTERM) produces `ClaudeInterrupted`, allowing callers to distinguish user interruption from process crashes.

### Testability

- Exception classes and outcome parsing are unit-testable in isolation.
- INFO tag detection in the streaming processor is testable with mock stream data.
- Auto-injection can be tested by verifying prompt content before/after `run_batch()` processing.

---

## Scenarios and Workflows

### Scenario 1 (Primary): Task Execution with Outcome Parsing

A caller (e.g., trunk_mode) invokes `run_batch()` to execute a task. `run_batch()` auto-injects outcome tag instructions, streams dots and INFO messages during execution, parses the outcome on completion, and returns `ClaudeResult` with `outcome=SUCCESS` and the commit SHA as payload. The caller inspects the payload and verifies HEAD advancement.

### Scenario 2: Retry on Process Failure

Claude crashes mid-execution (non-zero exit code). `run_batch()` prints platform diagnostics and raises `ClaudeProcessError`. The caller's retry loop catches `ClaudeRetryableError` and retries.

### Scenario 3: Fail Fast on Explicit Failure

Claude runs to completion but emits `<FAILURE>could not resolve merge conflict</FAILURE>`. `run_batch()` prints platform diagnostics and raises `ClaudeFailure` with the failure explanation as payload. The caller does not retry.

### Scenario 4: Missing Outcome Tag

Claude exits 0 but produces no outcome tag (malformed output). `run_batch()` raises `ClaudeMissingOutcomeTag`. The caller treats this as a fatal error.

### Scenario 5: NOTHING-TO-DO

Scaffolding invocation where the project already has the expected structure. Claude emits `<NOTHING-TO-DO>Scaffold already exists</NOTHING-TO-DO>`. `run_batch()` returns `ClaudeResult` with `outcome=NOTHING_TO_DO`. The caller skips further processing.

### Scenario 6: INFO Messages During Streaming

During a long task execution, Claude emits `<INFO>Reading source files</INFO>`, then later `<INFO>Running tests</INFO>`. The streaming processor displays each INFO message on its own line between progress dots.

### Scenario 7: User Interruption (CTRL-C)

User presses CTRL-C during execution. The process returns exit code 130. `run_batch()` raises `ClaudeInterrupted`. The caller can distinguish this from a crash and handle accordingly.

### Scenario 8: Template with Front-Matter Payload Description

A template (e.g., `task_execution.j2`) includes YAML front-matter declaring `outcome.success: "the commit SHA in format: task implemented: COMMIT_SHA"`. `run_batch()` parses the front-matter, strips it from the prompt, and renders the outcome tag template with the custom success payload description. The injected instructions tell Claude specifically what to put inside the `<SUCCESS>` tag.

### Scenario 9: Template with Front-Matter Including NOTHING-TO-DO

A template (e.g., `scaffolding.j2`) includes front-matter with both `outcome.success` and `outcome.nothing_to_do`. The injected instructions include all three outcome tags. A template without `outcome.nothing_to_do` in its front-matter only gets SUCCESS and FAILURE instructions.

### Scenario 10: Template with Inline Tags (Override)

A template includes its own `<SUCCESS>` tag instructions directly in the template body (e.g., a complex payload format via `{% if not interactive %}`). `run_batch()` detects existing tags in the prompt and skips auto-injection entirely. Outcome parsing works the same regardless of injection source.

### Scenario 11: Callers Without Tag Expectations

Callers like create_plan and summary_reports currently use stdout directly without checking tags. With auto-injection, Claude wraps output in `<SUCCESS>` tags. These callers access `result.payload` (the content inside the tag) instead of raw stdout.

---

## Constraints and Assumptions

1. **Stream-json format is stable.** Each line is a complete JSON object. INFO tags will not span line boundaries.
2. **Outcome tags appear in stdout.** Tags like `<SUCCESS>...</SUCCESS>` are emitted by Claude as text content within the stream-json output, not as JSON fields.
3. **One outcome tag per invocation.** `run_batch()` expects exactly one of SUCCESS, FAILURE, or NOTHING-TO-DO in the final output. If multiple appear, the last one wins.
4. **INFO is advisory only.** Claude decides what to report and when. The platform does not validate or act on INFO content.
5. **No change to interactive mode.** All changes are scoped to `run_batch()` and non-interactive execution paths.
6. **Templates have access to `interactive` variable.** This is already the case — templates use `{% if not interactive %}` conditionally.
7. **YAML front-matter is optional.** Templates without front-matter work fine — `run_batch()` uses generic defaults. Front-matter follows Jekyll conventions: delimited by `---` lines at the start of the prompt.
8. **Front-matter is stripped before execution.** The YAML block is consumed by `run_batch()` and not passed to Claude as part of the prompt.

---

## Acceptance Criteria

1. **Auto-injection works with generic defaults:** `run_batch()` appends outcome tag instructions when the prompt has no tags and no front-matter. Injected instructions include SUCCESS and FAILURE only (no NOTHING-TO-DO).
2. **Auto-injection skips when tags present:** If the prompt already contains `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>`, no injection occurs. Verified with a template that includes its own tags.
3. **Front-matter parameterizes injection:** A template with YAML front-matter declaring `outcome.success` produces injected instructions with the custom payload description. Front-matter is stripped from the prompt before execution.
4. **Front-matter controls NOTHING-TO-DO inclusion:** A template with `outcome.nothing_to_do` in front-matter gets NOTHING-TO-DO instructions injected. A template without it does not.
5. **Outcome parsing returns correct result:** On `<SUCCESS>` or `<NOTHING-TO-DO>`, `ClaudeResult` contains the correct `outcome` enum and `payload` string.
6. **Failure raises correct exception:** On `<FAILURE>`, `ClaudeFailure` is raised with the payload. On non-zero exit code, `ClaudeProcessError` or `ClaudeInterrupted` is raised. On missing tag, `ClaudeMissingOutcomeTag` is raised.
7. **Exceptions carry diagnostics:** All exceptions include the full `ClaudeResult` with exit code, output, and diagnostics.
8. **Platform diagnostics printed before raise:** Exit code, permission denials, error messages, and last messages are printed to stderr before the exception propagates.
9. **HEAD logic removed from platform:** `print_task_failure_diagnostics()` no longer accepts or prints `head_before`/`head_after`. `check_claude_success()` is removed from `claude_runner.py`.
10. **INFO messages display correctly:** During streaming, `<INFO>` tags produce indented messages between progress dot lines.
11. **Tag instructions removed from templates:** `task_execution.j2`, `commit_recovery.j2`, and `scaffolding.j2` no longer contain inline SUCCESS/FAILURE/NOTHING-TO-DO tag instructions. Instead, they declare payload descriptions via YAML front-matter.
12. **All existing callers migrated:** trunk_mode, worktree_mode, commit_recovery, project_scaffolding, PR triage, PR fix, create_plan, summary_reports, and analyze_sessions use the new exception-based error handling.
13. **Backward compatibility preserved:** Existing `ClaudeResult` fields (`returncode`, `output`, `diagnostics`) remain unchanged and accessible.

---

## Change History

### 2026-03-06: Add YAML front-matter for outcome tag parameterization

Templates can now declare optional YAML front-matter (Jekyll-style) to parameterize the auto-injected outcome tag instructions. Front-matter defines custom payload descriptions for SUCCESS and optionally enables NOTHING-TO-DO. Three-tier resolution: inline tags → front-matter → generic defaults.

### 2026-03-03: Initial specification

Created from discussion (Q1–Q15) covering auto-injection, exception hierarchy, INFO streaming, diagnostics refactoring, and caller migration patterns.
