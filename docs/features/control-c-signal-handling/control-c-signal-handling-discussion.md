# Control-C Signal Handling — Discussion

## Codebase Analysis (Pre-Discussion)

Key findings from exploring `src/i2code/implement/`:

- **Three execution modes**: trunk, isolate, worktree — each invokes subprocesses differently
- **Claude invocation**:
  - Interactive: `subprocess.run(cmd)` — inherits terminal, Ctrl+C propagates naturally
  - Non-interactive: `subprocess.Popen()` with reader threads for stdout/stderr
- **Isolarium invocation**: `subprocess.run(isolarium_cmd)` — blocking call
- **Dead signal handling code**: `branch_lifecycle.py` has `register_signal_handlers()` and `cleanup_on_interrupt()` but they are never called
- **No graceful shutdown**: failures call `sys.exit(1)` without cleanup
- **No process group management**: child processes not explicitly cleaned up on interrupt

## Classification

**C. Platform/infrastructure capability**

**Rationale:** This is hardening the process lifecycle management of an existing internal tool (`i2code implement`). It's not a new user-facing feature, not validating an architectural concern, and not an example. It improves the robustness and operational behavior of the development workflow platform.

## Questions & Answers

### Q1: When the user presses Ctrl+C during `i2code implement`, what's the primary goal?

Options:
- A. Save state and exit gracefully
- B. Forward the signal and let the subprocess decide
- C. Two-stage interrupt (first = graceful, second = force-kill)
- D. Something else

**Answer:** A — save state and exit gracefully.

**Follow-up from user:** "Is there any actual state to save?"

**Analysis:** Not much that isn't already saved:
- Task completion is tracked in the plan file itself (persisted by Claude on commit)
- WorkflowState (slice_number, processed feedback IDs) is already saved after each feedback processing cycle
- If interrupted mid-task, there's nothing meaningful to save — the task would be re-run

**Conclusion:** The real value of proper Ctrl+C handling is:
1. Clean subprocess termination — don't leave orphan `claude` or `isolarium` processes
2. Clean exit — no Python `KeyboardInterrupt` stack trace
3. Edge-case state saving (interrupt between feedback processing and next save)

### Q2: Which subprocess scenarios concern you most?

Options:
- A. Interactive Claude (`subprocess.run`) — Ctrl+C propagates naturally
- B. Non-interactive Claude (`subprocess.Popen` + reader threads)
- C. Isolarium (`subprocess.run`) — long-running VM session
- D. All of the above

**Answer:** B + C (non-interactive cases only). But never cleanup the VM itself.

**Derived conclusions:**
- Interactive Claude is out of scope — Ctrl+C already propagates naturally via terminal inheritance
- Non-interactive Claude (Popen): need to terminate the `claude` child process and join reader threads cleanly
- Isolarium: need to terminate the `isolarium` subprocess, but must NOT destroy/cleanup the VM — just stop the `i2code` process's wait on it
- The VM is a persistent resource the user may want to inspect or reconnect to

### Q3: For non-interactive Claude (Popen + reader threads), what should "terminate" mean?

Options:
- A. `process.terminate()` (SIGTERM) first, escalate to `process.kill()` (SIGKILL) after timeout
- B. `process.kill()` (SIGKILL) immediately
- C. `process.terminate()` (SIGTERM) with no escalation

**Answer:** A — SIGTERM first, escalate to SIGKILL after a timeout.

**Default assumption:** 5-second timeout before escalation to SIGKILL. Easily adjustable later.

### Q4: For the isolarium case, what should Ctrl+C do?

Options:
- A. Send SIGTERM to the `isolarium` process only (detach from VM session)
- B. Send SIGTERM to `isolarium` process, which propagates into the VM
- C. Just exit the Python parent, let OS clean up

**Answer:** Isolarium's own signal handling is not yet implemented — that's a separate piece of work.

**Derived conclusion:** For this feature, `i2code implement` should apply the same SIGTERM-then-SIGKILL pattern to the `isolarium` subprocess (same as non-interactive Claude). Whatever isolarium does with that signal is isolarium's concern. The key constraint is: never destroy/cleanup the VM itself from `i2code`'s side.

### Q5: Should `i2code implement` print a message when handling Ctrl+C?

Options:
- A. Minimal — just `"\nInterrupted."` and exit
- B. Informative — print what's happening (e.g., `"\nInterrupted. Terminating claude process... Done."`)
- C. Silent — no message, just clean exit

**Answer:** B — Informative. User should see what cleanup is happening so they know it's not hung.

### Q6: Where should the signal handling logic live architecturally?

Options:
- A. Centralized signal handler — one SIGINT handler at top of `ImplementCommand.execute()`
- B. Per-call `try/except KeyboardInterrupt` — wrap each subprocess call locally
- C. Context manager — `ManagedSubprocess` wraps Popen, handles cleanup in `__exit__`

**Answer:** C — Context manager.

**Rationale:**
- No global mutable state (unlike A)
- No duplicated cleanup logic (unlike B)
- Pythonic — `with` statement is the standard idiom for resource cleanup
- Testable in isolation with mock processes
- Fits existing Popen + threads pattern in `claude_runner.py`

**Files impacted:**
- New: `src/i2code/implement/managed_subprocess.py`
- Modified: `claude_runner.py` (non-interactive), `isolate_mode.py` (switch to Popen)
- Removable dead code: `branch_lifecycle.py` signal handler functions
- Out of scope: `run_claude_interactive()`, `github_client.py`

### Q7: Should the context manager also handle reader threads?

Options:
- A. Context manager handles subprocess + threads — accepts optional thread references, joins them after terminating the process
- B. Context manager handles subprocess only — thread management stays in caller

**Answer:** A — Context manager handles both. Threads read from the process's pipes, so they naturally finish once the process terminates. Joining them in the context manager ensures complete cleanup in one place.

### Q8: What exit code should `i2code implement` return after a Ctrl+C interruption?

Options:
- A. 130 — Unix convention for "terminated by SIGINT" (128 + 2)
- B. 1 — Generic failure
- C. Doesn't matter

**Answer:** A — exit code 130. Standard Unix convention, lets callers distinguish "user interrupted" from "actual failure".

