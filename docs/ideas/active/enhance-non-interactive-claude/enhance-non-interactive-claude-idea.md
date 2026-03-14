# Enhance Non-Interactive Claude

## Problem

Non-interactive Claude invocations (`run_batch()`) have three issues:

1. **Inconsistent prompt construction** — SUCCESS/FAILURE/NOTHING-TO-DO tag instructions are duplicated across templates, some include them, some don't.
2. **Scattered result checking** — Each caller implements its own ad-hoc pattern for detecting success/failure (string search for tags, exit code checks, HEAD advancement). The `<FAILURE>` tag is defined in prompts but never parsed.
3. **Opaque progress** — Users see only a stream of dots (`.....`) with no indication of what Claude is doing.

## Solution

### 1. Auto-inject outcome tag instructions

- `run_batch()` appends a standard prompt block (Jinja2 template) instructing Claude to wrap output in `<SUCCESS>`, `<FAILURE>`, or `<NOTHING-TO-DO>` tags.
- Templates define the *payload* (what goes inside the tags). The platform defines the *envelope* (the tags themselves).
- Two-layer approach: templates can include their own tag instructions for special cases (using `{% if not interactive %}`). `run_batch()` checks if tags are already present before injecting.
- Remove existing tag instructions from `task_execution.j2`, `commit_recovery.j2`, etc.

### 2. Centralize result checking with exceptions

`run_batch()` parses the outcome after process completion and either returns or raises:

- **SUCCESS / NOTHING_TO_DO** — Returns enhanced `ClaudeResult` with `outcome` (enum) and `payload` (tag content). Callers inspect and interpret the payload.
- **FAILURE** — Raises an exception. Two categories:
  - `ClaudeRetryableError` (subtypes: `ClaudeProcessError`, `ClaudeInterrupted`) — process crashed, timed out, or was interrupted. Caller may retry.
  - `ClaudeFailure` (subtype: `ClaudeMissingOutcomeTag`) — Claude explicitly failed or didn't produce outcome tags. Retrying won't help.

Platform diagnostics (exit code, permission denials, error messages) are printed before raising. Caller-specific context (HEAD before/after, attempt count) stays with callers.

Refactor `print_task_failure_diagnostics()` to remove `head_before`/`head_after` params — HEAD-related logic moves to caller-level functions.

`check_claude_success()` is removed or moved to a caller utility — HEAD advancement is a caller concern, not a platform concern.

### 3. Support `<INFO>` messages during streaming

- Auto-injected instructions tell Claude to emit `<INFO>` messages periodically to indicate progress. Claude decides granularity.
- Streaming processor detects `<INFO>` tags and displays them:
  - Dots remain as baseline progress indicator on a single line
  - When an INFO tag is detected: newline, print INFO message, resume dots on next line
- Example output:
  ```
  .......
    Reading source files
  .........
    Running tests
  ....
    Committing changes
  ...
  ```
