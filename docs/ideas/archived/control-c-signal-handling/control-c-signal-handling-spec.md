# Signal Handling (Ctrl+C, Ctrl+Z) — Platform Capability Specification

## Purpose and Context

`i2code implement` orchestrates long-running subprocesses — Claude CLI invocations and isolarium VM sessions — that can run for minutes or longer. Today, pressing Ctrl+C during these operations produces unpredictable behavior: Python `KeyboardInterrupt` stack traces, orphaned child processes, and no cleanup of reader threads. Pressing Ctrl+Z has no effect — the process cannot be suspended.

This capability adds structured signal handling for non-interactive subprocess scenarios: Ctrl+C (SIGINT) for clean termination and Ctrl+Z (SIGTSTP) for suspend/resume, with informative user feedback and proper resource cleanup.

### Current State

- **Non-interactive Claude** (`run_claude_with_output_capture` in `claude_runner.py`): Uses `subprocess.Popen` with two reader threads (stdout, stderr). On Ctrl+C, `process.wait()` raises `KeyboardInterrupt`, but the child process and threads are not explicitly terminated.
- **Isolarium** (`RealSubprocessRunner.run` in `isolate_mode.py`): Uses `subprocess.run()`, a blocking call. On Ctrl+C, behavior depends on OS signal propagation — no explicit handling.
- **Dead signal handling code** in `branch_lifecycle.py`: `register_signal_handlers()`, `_handle_interrupt()`, and `cleanup_on_interrupt()` exist but are never called anywhere in the codebase.
- **Interactive Claude** (`run_claude_interactive` in `claude_runner.py`): Uses `subprocess.run()` with terminal inheritance. Ctrl+C propagates naturally — no changes needed.
- **Ctrl+Z (SIGTSTP)**: Has no effect during subprocess execution. Child processes share the parent's process group, but Python's `process.wait()` retries on `EINTR` after suspend/resume, and reader threads complicate the behavior. In interactive mode, Claude's TUI consumes Ctrl+Z in raw mode before it generates a signal.

## Consumers

| Consumer | Usage |
|---|---|
| `claude_runner.py` — `run_claude_with_output_capture()` | Wraps the non-interactive Claude `Popen` call and its reader threads in the context manager |
| `isolate_mode.py` — `RealSubprocessRunner.run()` | Switches from `subprocess.run()` to `Popen` via the context manager |
| Future subprocess call sites in `i2code implement` | Can adopt the same context manager for consistent interrupt handling |

### Out of Scope

| Component | Reason |
|---|---|
| `run_claude_interactive()` | Ctrl+C and Ctrl+Z propagate naturally via terminal inheritance (Ctrl+Z is consumed by Claude's TUI in raw mode) |
| `github_client.py` (`gh` CLI calls) | Short-lived commands, not long-running |
| Isolarium VM lifecycle | VM must never be destroyed by `i2code`; isolarium's own signal handling is a separate work item |
| `MockClaudeRunner` | Test double; does not need production signal handling |

## Capabilities and Behaviors

### CAP-1: ManagedSubprocess Context Manager

A context manager that wraps `subprocess.Popen` and optional reader threads, providing structured cleanup on `KeyboardInterrupt` and signal forwarding for suspend/resume.

**Prerequisite:** The child process must be started with `start_new_session=True` so it has its own process group. This prevents the terminal from sending signals directly to the child and gives the context manager explicit control over signal forwarding for both Ctrl+C and Ctrl+Z.

**Normal flow (no interrupt):**
1. Caller creates a `Popen` process (with `start_new_session=True`) and optionally starts reader threads.
2. Caller enters the context manager, passing the process and thread references.
3. `__enter__` installs SIGTSTP and SIGCONT handlers for suspend/resume forwarding (see CAP-5).
4. Caller calls `process.wait()` (or equivalent) inside the `with` block.
5. On normal exit, `__exit__` restores original signal handlers. No other cleanup needed (process already finished).

**Interrupt flow (Ctrl+C):**
1. `KeyboardInterrupt` propagates to the `with` block.
2. `__exit__` catches the exception and performs cleanup:
   - Prints `"\nInterrupted. Terminating <label> process..."` to stderr.
   - Sends `SIGTERM` to the child process via `process.terminate()`.
   - Waits up to 5 seconds for the process to exit.
   - If still running after timeout, sends `SIGKILL` via `process.kill()` and prints an escalation message.
   - Joins all registered reader threads (with a timeout).
   - Prints `"Done."` to stderr.
   - Restores original signal handlers.
3. `__exit__` suppresses the `KeyboardInterrupt` (returns `True`).
4. The caller is responsible for exiting with code 130.

### CAP-2: Informative Cleanup Messages

During interrupt handling, print status messages to stderr so the user knows the process is cleaning up and not hung:

- `"\nInterrupted. Terminating claude process..."` (or `"isolarium process"`)
- `"Force-killing claude process..."` (if SIGTERM timeout expires)
- `"Done."`

### CAP-3: Exit Code 130

After the context manager completes interrupt cleanup, the caller exits with code 130 (Unix convention: 128 + SIGINT signal number 2). This lets callers distinguish user interruption from other failures.

### CAP-4: Dead Code Removal

Remove the unused signal handling functions from `branch_lifecycle.py`:
- `register_signal_handlers()`
- `_handle_interrupt()`
- `cleanup_on_interrupt()`
- `_interrupt_state` module-level dict

These are replaced by the context manager approach.

### CAP-5: Suspend/Resume Signal Forwarding (Ctrl+Z)

The context manager installs signal handlers that forward SIGTSTP and SIGCONT to the child process group, enabling standard Unix suspend/resume behavior.

**Suspend flow (Ctrl+Z):**
1. User presses Ctrl+Z → terminal sends SIGTSTP to the parent process.
2. The installed SIGTSTP handler:
   - Forwards SIGTSTP to the child's process group via `os.killpg(process.pid, signal.SIGTSTP)`.
   - Resets the SIGTSTP handler to `SIG_DFL` (so the parent can actually suspend).
   - Re-raises SIGTSTP on the parent via `os.kill(os.getpid(), signal.SIGTSTP)`.
3. The parent suspends. The shell prints `[1]+ Stopped` and the user gets their prompt back.

**Resume flow (`fg`):**
1. User types `fg` → shell sends SIGCONT to the parent.
2. The installed SIGCONT handler:
   - Forwards SIGCONT to the child's process group via `os.killpg(process.pid, signal.SIGCONT)`.
   - Re-installs the custom SIGTSTP handler (so the next Ctrl+Z works).
3. Both parent and child resume execution. `process.wait()` continues waiting.

## High-Level API

### ManagedSubprocess

```python
class ManagedSubprocess:
    """Context manager for subprocess lifecycle with Ctrl+C and Ctrl+Z handling.

    The child process must be started with start_new_session=True so that
    signals can be explicitly forwarded to its process group.

    Args:
        process: A subprocess.Popen instance (started with start_new_session=True).
        label: Human-readable name for status messages (e.g., "claude", "isolarium").
        threads: Optional list of threading.Thread instances to join on cleanup.
        terminate_timeout: Seconds to wait after SIGTERM before escalating to SIGKILL.
    """

    def __init__(
        self,
        process: subprocess.Popen,
        label: str,
        threads: Optional[List[threading.Thread]] = None,
        terminate_timeout: float = 5.0,
    ): ...

    def __enter__(self) -> "ManagedSubprocess":
        """Install SIGTSTP and SIGCONT handlers for suspend/resume forwarding."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Restore signal handlers. On KeyboardInterrupt: terminate process,
        join threads, suppress exception."""
        ...
```

### Integration with claude_runner.py

```python
# In run_claude_with_output_capture():
process = subprocess.Popen(
    cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    start_new_session=True,
)
# ... start reader threads ...
with ManagedSubprocess(process, label="claude", threads=[stdout_thread, stderr_thread]):
    process.wait()
# ... parse output (only reached on normal exit) ...
```

### Integration with isolate_mode.py

```python
# In RealSubprocessRunner.run():
process = subprocess.Popen(cmd, start_new_session=True)
with ManagedSubprocess(process, label="isolarium"):
    process.wait()
return process.returncode
```

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Cleanup latency** | SIGTERM phase completes within 5 seconds; SIGKILL is immediate. Total cleanup under 6 seconds. |
| **No orphan processes** | After `i2code implement` exits (whether normal or interrupted), no child `claude` or `isolarium` processes remain running. |
| **No hung threads** | Reader threads are joined with a timeout; the process does not hang waiting for threads. |
| **No stack traces** | `KeyboardInterrupt` is caught and suppressed; user sees informative messages, not a traceback. |
| **Testability** | The context manager is unit-testable with mock `Popen` and `Thread` objects, without spawning real subprocesses. |

## Scenarios and Workflows

### Scenario 1 (Primary): Ctrl+C During Non-Interactive Claude Execution

**Precondition:** `i2code implement --non-interactive <idea-dir>` is running. Claude is executing a task via `run_claude_with_output_capture`. Progress dots are printing.

**Trigger:** User presses Ctrl+C.

**Expected behavior:**
1. Progress dots stop.
2. Stderr prints: `"\nInterrupted. Terminating claude process..."`
3. SIGTERM is sent to the Claude child process.
4. Claude exits within 5 seconds.
5. Reader threads (stdout, stderr) drain and are joined.
6. Stderr prints: `"Done."`
7. `i2code implement` exits with code 130.
8. No orphan `claude` process remains.

### Scenario 2: Ctrl+C During Isolarium Execution

**Precondition:** `i2code implement --isolate <idea-dir>` is running. The isolarium subprocess is active.

**Trigger:** User presses Ctrl+C.

**Expected behavior:**
1. Stderr prints: `"\nInterrupted. Terminating isolarium process..."`
2. SIGTERM is sent to the `isolarium` subprocess.
3. Isolarium exits (or is force-killed after 5 seconds).
4. Stderr prints: `"Done."`
5. `i2code implement` exits with code 130.
6. The isolarium VM continues to exist (not destroyed).

### Scenario 3: SIGTERM Timeout — Escalation to SIGKILL

**Precondition:** Non-interactive Claude is running. The Claude process does not respond to SIGTERM.

**Trigger:** User presses Ctrl+C.

**Expected behavior:**
1. Stderr prints: `"\nInterrupted. Terminating claude process..."`
2. SIGTERM is sent to the Claude child process.
3. After 5 seconds, Claude has not exited.
4. Stderr prints: `"Force-killing claude process..."`
5. SIGKILL is sent.
6. Process exits immediately.
7. Reader threads are joined.
8. Stderr prints: `"Done."`
9. `i2code implement` exits with code 130.

### Scenario 4: Normal Exit — No Interrupt

**Precondition:** Non-interactive Claude is running inside the context manager.

**Trigger:** Claude completes normally (exit code 0).

**Expected behavior:**
1. `process.wait()` returns normally.
2. `__exit__` detects no exception, performs no cleanup action.
3. Execution continues past the `with` block to parse output.
4. No interrupt messages are printed.

### Scenario 5: Ctrl+Z During Non-Interactive Claude — Suspend and Resume

**Precondition:** `i2code implement --non-interactive <idea-dir>` is running. Claude is executing a task via `run_claude_with_output_capture`.

**Trigger:** User presses Ctrl+Z.

**Expected behavior:**
1. SIGTSTP is forwarded to the Claude child process group.
2. Both `i2code` and the Claude child process suspend.
3. Shell prints `[1]+ Stopped` and the user gets their prompt back.
4. User types `fg`.
5. SIGCONT is forwarded to the Claude child process group.
6. Both processes resume. `process.wait()` continues waiting.
7. Execution proceeds as if no suspend occurred.

### Scenario 6: Ctrl+C During Interactive Claude (Out of Scope — Unchanged)

**Precondition:** `i2code implement <idea-dir>` is running in interactive mode. Claude's TUI is displayed.

**Trigger:** User presses Ctrl+C.

**Expected behavior:** Same as today — Ctrl+C propagates directly to Claude via terminal inheritance. No change in this feature.

## Constraints and Assumptions

1. **Python signal handling model:** `KeyboardInterrupt` is raised in the main thread when SIGINT is received. The context manager relies on this standard Python behavior.
2. **`process.terminate()` sends SIGTERM on Unix.** This is a Unix-only tool; Windows behavior is not considered.
3. **Reader threads will exit when pipes close.** Once the child process is terminated, its stdout/stderr pipes close, causing the reader threads' `read()` calls to return empty bytes and exit their loops.
4. **Isolarium VM is never destroyed.** The context manager only terminates the `isolarium` CLI process. Whatever happens inside the VM is isolarium's responsibility.
5. **The 5-second SIGTERM timeout is a default.** It is a constructor parameter and can be adjusted without code changes.
6. **Thread join timeout should match terminate timeout.** Reader threads should be joined with the same or slightly longer timeout to avoid blocking indefinitely if a thread is stuck.
7. **`start_new_session=True` isolates the child process group.** This is required for both Ctrl+C and Ctrl+Z handling. Without it, the terminal sends signals directly to all processes in the group, bypassing the context manager's explicit signal forwarding.
8. **Signal handlers are only effective in the main thread.** Python only allows signal handlers to be installed in the main thread. The context manager assumes it is used from the main thread.
9. **SIGTSTP handler must reset to SIG_DFL before re-raising.** Otherwise the custom handler intercepts the re-raised signal, causing infinite recursion instead of suspension.

## Acceptance Criteria

1. **AC-1:** When Ctrl+C is pressed during `run_claude_with_output_capture`, the Claude child process is terminated, reader threads are joined, an informative message is printed, and `i2code implement` exits with code 130. No `KeyboardInterrupt` traceback is shown.

2. **AC-2:** When Ctrl+C is pressed during isolarium execution via `RealSubprocessRunner.run`, the isolarium subprocess is terminated, an informative message is printed, and `i2code implement` exits with code 130. The isolarium VM is not destroyed.

3. **AC-3:** If the child process does not exit within 5 seconds of SIGTERM, it is escalated to SIGKILL, and an escalation message is printed.

4. **AC-4:** When no interrupt occurs, the context manager has no observable effect on normal execution flow or return values.

5. **AC-5:** The dead signal handling code in `branch_lifecycle.py` (`register_signal_handlers`, `_handle_interrupt`, `cleanup_on_interrupt`, `_interrupt_state`) is removed.

6. **AC-6:** The `ManagedSubprocess` context manager is unit-testable with mock objects (no real subprocesses needed in tests).

7. **AC-7:** When Ctrl+Z is pressed during non-interactive Claude or isolarium execution, both `i2code` and the child process suspend. Resuming with `fg` resumes both processes and execution continues normally.

8. **AC-8:** The context manager restores original signal handlers (SIGTSTP, SIGCONT) on exit, whether the exit is normal or due to an interrupt.
