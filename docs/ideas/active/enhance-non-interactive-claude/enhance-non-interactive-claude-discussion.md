# Discussion: Enhance Non-Interactive Claude

## Classification

**Type: C. Platform/infrastructure capability**

**Rationale:** This feature improves the internal plumbing that all non-interactive Claude invocations share. It standardizes prompt construction, centralizes result parsing, and adds streaming progress feedback. No end-user-visible behavior changes — it makes the platform more consistent and maintainable for developers building on top of `claude_runner.py`.

## Codebase Analysis (pre-discussion)

### Current Architecture

- **`claude_runner.py`**: Core module with `ClaudeRunner` class. `run_batch()` delegates to `run_claude_with_output_capture()`.
- **`command_builder.py`**: Constructs commands using Jinja2 templates. Non-interactive mode adds `--verbose --output-format=stream-json -p`.
- **Progress output**: One dot per JSON line via `_print_dot_per_line()`.
- **No custom exceptions**: Callers use `sys.exit(1)` or `continue` on failure.

### Current SUCCESS/FAILURE Tag Usage (scattered and inconsistent)

| Caller | Checks SUCCESS tag? | Checks FAILURE? | Checks HEAD? | Checks exit code? |
|--------|---------------------|-----------------|--------------|-------------------|
| trunk_mode.py | Yes (string search) | No | Yes | Yes |
| worktree_mode.py | Yes (string search) | No | Yes | Yes |
| commit_recovery.py | Yes (string search) | No | Yes | Yes |
| project_scaffolding.py | Yes + NOTHING-TO-DO | No | No | No |
| PR triage | No (uses JSON) | No | No | No |
| PR fix | No | No | Yes | No |

### Templates that include tags in prompts

- `task_execution.j2` — SUCCESS/FAILURE
- `commit_recovery.j2` — SUCCESS/FAILURE
- `project_scaffolding.j2` — SUCCESS/FAILURE/NOTHING-TO-DO (noted in idea)
- `triage_feedback.j2` — No tags (JSON-based)

## Questions and Answers

### Q1: How to handle divergent output patterns across callers?

**Context:** The content inside SUCCESS tags varies by caller:
- Task execution: `<SUCCESS>task implemented: COMMIT_SHA</SUCCESS>`
- Commit recovery: `<SUCCESS>recovery commit: COMMIT_SHA</SUCCESS>`
- Scaffolding: `<SUCCESS>...</SUCCESS>` or `<NOTHING-TO-DO>No changes needed</NOTHING-TO-DO>`
- PR triage: Raw JSON (no tags at all)

**User observation:** The contents of `<SUCCESS>` are task-specific — commit SHAs, JSON, etc. The tag is just an envelope; the payload varies.

### Q2: Should `run_batch()` auto-inject tag instructions or leave them in templates?

**A: Auto-inject with separation of concerns.**

- Templates define the *payload* — e.g., "output the commit SHA" or "output JSON with will_fix and needs_clarification"
- `run_batch()` auto-appends a standard block instructing Claude to wrap the output in `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>` tags
- Existing tag instructions are removed from individual templates
- This cleanly separates the envelope (platform concern) from the payload (task concern)

### Q3: How should `run_batch()` report outcomes — exceptions vs result object?

**Context:** There are three outcomes: SUCCESS, FAILURE, NOTHING-TO-DO.

**User observation:** NOTHING-TO-DO is another special case — currently only used by scaffolding ("scaffolding already exists"). It's success-adjacent but distinct from SUCCESS (no commit made, no work done).

**A: Always available.** The auto-injected instructions always include all three tags. `run_batch()` returns a result object with `outcome` (SUCCESS / FAILURE / NOTHING_TO_DO) and `payload`. Callers that don't care about NOTHING-TO-DO just treat it like SUCCESS.

### Q4: How should `run_batch()` report outcomes — exceptions vs result object?

**B: FAILURE raises, others return.** `run_batch()` raises an exception on FAILURE (with diagnostics and payload). SUCCESS and NOTHING_TO_DO return normally in the result object with outcome + payload.

Additionally: `print_task_failure_diagnostics()` should be called inside `run_batch()` on failure, but the head_before/head_after lines are caller-specific context — that should be extracted so callers can add their own context before the exception propagates.

#### Caller failure patterns observed in code:

| Caller | Failure behavior | Caller-specific context |
|--------|-----------------|------------------------|
| trunk_mode | `continue` (retry) or `sys.exit(1)` | head before/after, attempt count |
| worktree_mode | `continue` (retry) or `sys.exit(1)` | head before/after, attempt count |
| commit_recovery | `return False`, caller retries up to 2x | head before/after |
| scaffolding | print scaffolding-specific message | none |
| PR triage | `return None` (warning, skip) | none |
| PR fix | `return None` (warning, skip) | head before/after |

### Q5: Should there be one exception type or separate types for different failure causes?

**Context from retry analysis in trunk_mode/worktree_mode:**

The retry loop has a clear two-tier structure:

```
for attempt in range(1, max_attempts + 1):
    # Tier 1: Process-level failure → RETRY
    if not check_claude_success(returncode, head_before, head_after):
        print_task_failure_diagnostics(...)
        continue    # ← retry

    # Tier 2: Claude completed but no SUCCESS tag → FATAL (no retry)
    if non_interactive and "<SUCCESS>" not in stdout:
        print_task_failure_diagnostics(...)
        sys.exit(1) # ← immediate exit, no retry

    # Tier 3: Post-conditions not met → RETRY
    if not is_task_completed(...):
        continue    # ← retry
```

**Two distinct failure categories:**
1. **Retryable** — process crashed, timed out, or post-conditions not met. Transient; worth retrying.
2. **Fatal** — Claude ran to completion but explicitly failed (FAILURE tag) or produced no outcome tag. Retrying the same prompt won't help.

**User observation:** Some errors should trigger retry, others should fail immediately.

**User feedback:** "Task" is too specific — `run_batch()` is used for tasks, recovery, scaffolding, triage, and fixes. Exception names should reflect the general `run_batch()` contract, not one caller.

**Proposed names:**
- `ClaudeRetryableError` — process-level failure (bad exit code, no HEAD advancement). Worth retrying.
- `ClaudeFailure` — explicit `<FAILURE>` tag or no outcome tag. Don't retry.

### Q6: Exception subtypes

**Agreed hierarchy:**

```
ClaudeRetryableError          ← catch to retry
├── ClaudeProcessError        ← non-zero exit code (crash, timeout)
└── ClaudeInterrupted         ← returncode 130 (CTRL-C / SIGTERM)

ClaudeFailure                 ← catch to fail fast; <FAILURE> tag with explanation
└── ClaudeMissingOutcomeTag   ← exit 0 but no SUCCESS/FAILURE/NOTHING-TO-DO tag found
```

All carry diagnostics (exit code, permission denials, error messages, last messages). Platform diagnostics printed by `run_batch()` before raising. Caller-specific context (head before/after, attempt count) stays with caller.

### Q7: What kind of INFO messages should Claude emit?

**C: Let Claude decide.** The auto-injected instructions tell Claude to emit `<INFO>` messages periodically to indicate progress, without prescribing granularity. Claude decides what's worth reporting.

### Q8: How should INFO messages be displayed?

**B (modified): Dots + INFO lines, dots on same line.**

Dots continue as baseline progress. When an INFO tag is detected in the stream, print a newline, print the INFO message on its own line, then resume dots on the same line after it. Example output:

```
.......
  Reading source files
.........
  Running tests
....
  Committing changes
...
```

Preserves history (scrollable), works in CI/non-TTY, and dots show that Claude is still working between INFO messages.

### Q9: Where should INFO tags be detected?

**Implementation detail — resolved.** INFO tags won't span JSON line boundaries (each stream-json line is a complete JSON object, and INFO content is short). Detection can happen in the streaming line processor — either raw string scan or JSON parsing. Exact approach deferred to implementation.

### Q10: When to detect SUCCESS/FAILURE/NOTHING-TO-DO tags?

**Keep existing behavior.** Parse from full stdout after process completes (post-completion), same as current `_parse_stream_json_output()`. Outcome tags are only meaningful once Claude is done.

### Q11: Should `run_batch()` check HEAD advancement?

**No.** `run_batch()` owns exit code + tag parsing. HEAD advancement is caller-specific (not all callers expect a commit, e.g., PR triage). Callers that care about commits check HEAD themselves. `check_claude_success()` can be removed or moved to a caller utility.

### Q12: What should `run_batch()` return on success?

**Enhance existing `ClaudeResult`** with two new fields:
- `outcome`: enum (SUCCESS / NOTHING_TO_DO)
- `payload`: string content extracted from inside the tag

No breaking change — existing fields (returncode, output, diagnostics) still available. New callers get the parsed outcome.

### Q13: Refactoring `print_task_failure_diagnostics()`

**Split into separate concerns:**
- `print_task_failure_diagnostics(claude_result)` — platform diagnostics only (exit code, permission denials, error messages, last messages). Remove `head_before`/`head_after` params.
- Head-related checking/printing moves to separate caller-level functions. Callers that care about HEAD advancement handle it themselves.

### Q14: Format for the auto-injected prompt block?

**Jinja2 template.** Consistent with existing prompt templates in `src/i2code/implement/templates/`. Even though the content is currently fixed, using a template keeps the approach uniform and allows future parameterization.

### Q15: Where does auto-injection happen?

**Two-layer approach:**

1. **Templates (special cases):** Templates already have access to `non_interactive`. If a template has special needs (e.g., custom payload format alongside the tags), it can include SUCCESS/FAILURE/NOTHING-TO-DO instructions itself.
2. **`run_batch()` (safety net):** Before execution, `run_batch()` checks if the prompt already contains the outcome tags. If not, it appends the standard tag instructions (rendered from a Jinja2 template). This way most templates don't need to think about it.

Most callers get tags for free via `run_batch()`. Special cases override in the template.

**Confirmed:** Templates already receive `interactive` and use `{% if not interactive %}` conditionally (e.g., `task_execution.j2:19`). Currently `task_execution.j2` and `commit_recovery.j2` include SUCCESS/FAILURE tags unconditionally (even for interactive runs). With the new approach, these templates remove their tag instructions. If a template needs a custom payload format, it uses `{% if not interactive %}` to include its own tags, and `run_batch()` detects they're already present and skips injection.

