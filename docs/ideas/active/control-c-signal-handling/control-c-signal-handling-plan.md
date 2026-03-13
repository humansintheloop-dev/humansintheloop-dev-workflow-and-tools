Now I have all the context I need. Let me generate the plan.

# Signal Handling (Ctrl+C, Ctrl+Z) — Implementation Plan

## Idea Type: C — Platform/infrastructure capability

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `uv run --with pytest pytest tests/implement/`), its exit code, and the last 20 lines of output

## Overview

Add structured signal handling to `i2code implement` for non-interactive subprocess scenarios. The `ManagedSubprocess` context manager wraps `subprocess.Popen` and optional reader threads, providing:

- **Ctrl+C (SIGINT):** Clean termination with SIGTERM → SIGKILL escalation, thread cleanup, informative messages, and exit code 130.
- **Ctrl+Z (SIGTSTP):** Suspend/resume via signal forwarding to the child process group.

Consumers: `run_claude_with_output_capture()` in `claude_runner.py` and `RealSubprocessRunner.run()` in `isolate_mode.py`. Dead signal handling code in `branch_lifecycle.py` is removed.

All tasks should be implemented using TDD.

### Key Files

| File | Role |
|------|------|
| `src/i2code/implement/managed_subprocess.py` | New — ManagedSubprocess context manager |
| `tests/implement/test_managed_subprocess.py` | New — Unit tests with mock Popen/Thread |
| `src/i2code/implement/claude_runner.py` | Modified — integrate context manager |
| `src/i2code/implement/isolate_mode.py` | Modified — convert to Popen + context manager |
| `src/i2code/implement/branch_lifecycle.py` | Modified — remove dead signal code |

### Test Runner

```bash
uv run --with pytest pytest tests/implement/
```

Existing CI (`.github/workflows/ci.yml`) already runs `./test-scripts/test-end-to-end.sh` which includes `test-unit.sh`, which discovers all tests under `tests/`. New test files in `tests/implement/` are automatically included.

---

## Steel Thread 1: ManagedSubprocess Context Manager with Ctrl+C Termination

Proves the core context manager works end-to-end with mock Popen and Thread objects: normal exit, interrupt termination, and SIGKILL escalation.

- [x] **Task 1.1: ManagedSubprocess has no effect on normal process exit**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_managed_subprocess.py -k test_normal_exit`
  - Observable: Context manager enters and exits without calling `process.terminate()` or `process.kill()`; no cleanup messages printed to stderr; original signal handlers restored after exit
  - Evidence: Test creates mock Popen (already finished), enters/exits context manager, asserts `terminate()` and `kill()` not called, stderr is empty, original signal handlers are restored
  - Steps:
    - [x] Create `src/i2code/implement/managed_subprocess.py` with `ManagedSubprocess` class — stub `__init__`, `__enter__`, `__exit__` with `raise NotImplementedError`
    - [x] Create `tests/implement/test_managed_subprocess.py` with a test that constructs `ManagedSubprocess` with a mock Popen, enters and exits the context manager normally, and asserts no termination methods called and no stderr output
    - [x] Implement `__init__` to store process, label, threads, and terminate_timeout
    - [x] Implement `__enter__` to save original signal handlers and return self
    - [x] Implement `__exit__` to restore original signal handlers on normal exit (no exception)

- [x] **Task 1.2: ManagedSubprocess terminates child on KeyboardInterrupt with cleanup messages**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_managed_subprocess.py -k test_keyboard_interrupt`
  - Observable: On `KeyboardInterrupt`: `process.terminate()` called, all threads joined with timeout, `"\nInterrupted. Terminating <label> process..."` and `"Done."` printed to stderr, exception suppressed (`__exit__` returns `True`), `interrupted` property is `True`
  - Evidence: Test enters context manager, simulates `KeyboardInterrupt` via `__exit__(KeyboardInterrupt, ...)`, asserts `terminate()` called, mock threads' `join()` called, stderr contains expected messages, and `managed.interrupted` is `True`
  - Steps:
    - [x] Write test that calls `__exit__` with `KeyboardInterrupt` exc_type, mock process that exits promptly after `terminate()`, and mock threads
    - [x] Implement `__exit__` to detect `KeyboardInterrupt`, call `process.terminate()`, wait for process with timeout, join threads, print cleanup messages to stderr, set `self.interrupted = True`, and return `True` to suppress the exception
    - [x] Write test with mock threads to verify all threads are joined with a timeout
    - [x] Implement thread joining with timeout matching `terminate_timeout`

- [x] **Task 1.3: ManagedSubprocess escalates to SIGKILL when SIGTERM times out**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_managed_subprocess.py -k test_sigkill_escalation`
  - Observable: When child process does not exit within `terminate_timeout` after SIGTERM, `process.kill()` is called and `"Force-killing <label> process..."` printed to stderr before `"Done."`
  - Evidence: Test mocks `process.wait()` to raise `subprocess.TimeoutExpired` after `terminate()`, asserts `process.kill()` called, stderr contains `"Force-killing claude process..."` followed by `"Done."`
  - Steps:
    - [x] Write test where mock process raises `TimeoutExpired` on first `wait(timeout=...)` after `terminate()`, then returns on second `wait()`
    - [x] Implement SIGKILL escalation: after `process.terminate()`, call `process.wait(timeout=terminate_timeout)`; on `TimeoutExpired`, print escalation message, call `process.kill()`, then `process.wait()`

---

## Steel Thread 2: Ctrl+Z Suspend/Resume Signal Forwarding

Adds SIGTSTP and SIGCONT handler installation to `__enter__`, enabling Unix suspend/resume when the child process is running.

- [x] **Task 2.1: ManagedSubprocess forwards SIGTSTP and SIGCONT to child process group**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_managed_subprocess.py -k test_signal_forwarding`
  - Observable: On `__enter__`, custom SIGTSTP and SIGCONT handlers are installed; SIGTSTP handler forwards signal to child process group via `os.killpg`; SIGCONT handler forwards to child and re-installs SIGTSTP handler; on `__exit__`, original SIGTSTP and SIGCONT handlers are restored (both normal and interrupt paths)
  - Evidence: Tests verify: (1) `signal.getsignal(SIGTSTP)` returns custom handler after `__enter__`, (2) SIGTSTP handler calls `os.killpg(process.pid, SIGTSTP)` (with mocked `os.killpg`), (3) SIGCONT handler calls `os.killpg(process.pid, SIGCONT)` and re-installs SIGTSTP handler, (4) after `__exit__`, signal handlers match originals
  - Steps:
    - [x] Write test that enters context manager and asserts custom SIGTSTP handler is installed (not `SIG_DFL`)
    - [x] Implement SIGTSTP handler installation in `__enter__`
    - [x] Write test that invokes the SIGTSTP handler directly (with mocked `os.killpg` and `os.kill`) and asserts it forwards SIGTSTP to child process group
    - [x] Implement SIGTSTP handler: forward to child group via `os.killpg`, reset to `SIG_DFL`, re-raise via `os.kill(os.getpid(), SIGTSTP)`
    - [x] Write test that invokes SIGCONT handler and asserts it forwards SIGCONT to child group and re-installs custom SIGTSTP handler
    - [x] Implement SIGCONT handler: forward to child group, re-install SIGTSTP handler
    - [x] Write test that verifies handlers are restored after `__exit__` on both normal exit and `KeyboardInterrupt`
    - [x] Verify all signal handler restoration works correctly on both exit paths

---

## Steel Thread 3: Integration with Non-Interactive Claude Execution

Wires ManagedSubprocess into `run_claude_with_output_capture()` so that Ctrl+C during non-interactive Claude produces clean termination.

- [x] **Task 3.1: run_claude_with_output_capture uses ManagedSubprocess for clean interrupt handling**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_claude_runner.py`
  - Observable: `subprocess.Popen` is called with `start_new_session=True`; `process.wait()` is wrapped in `ManagedSubprocess` context manager with `label="claude"` and both reader threads; when `ManagedSubprocess.interrupted` is `True` after the context manager exits, the function returns a `ClaudeResult` with `returncode=130`
  - Evidence: Existing tests continue to pass (normal behavior unchanged); new test patches `subprocess.Popen` and `ManagedSubprocess`, verifies `start_new_session=True` passed to Popen constructor and `ManagedSubprocess` instantiated with correct label and threads
  - Steps:
    - [x] Write test that patches `subprocess.Popen` in `claude_runner` module and asserts `start_new_session=True` is in the Popen kwargs
    - [x] Add `start_new_session=True` to the `Popen` call in `run_claude_with_output_capture()`
    - [x] Write test that patches `ManagedSubprocess` and verifies it is used as context manager with `label="claude"` and both reader threads
    - [x] Wrap `process.wait()` in `ManagedSubprocess` context manager, passing process, label, and thread list
    - [x] Write test for interrupt path: when `managed.interrupted` is `True`, function returns `ClaudeResult` with `returncode=130`
    - [x] Implement early return with `ClaudeResult(returncode=130, ...)` when interrupt detected
    - [x] Run full test suite to verify no regressions

---

## Steel Thread 4: Integration with Isolarium Execution and Dead Code Cleanup

Wires ManagedSubprocess into `RealSubprocessRunner.run()` and removes superseded dead code.

- [x] **Task 4.1: RealSubprocessRunner.run uses ManagedSubprocess for clean interrupt handling**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --with pytest pytest tests/implement/test_isolate_mode.py`
  - Observable: `RealSubprocessRunner.run()` uses `subprocess.Popen` with `start_new_session=True` instead of `subprocess.run()`; `process.wait()` wrapped in `ManagedSubprocess` with `label="isolarium"`; returns 130 when interrupted
  - Evidence: Existing tests continue to pass; new test patches `subprocess.Popen` and `ManagedSubprocess`, verifies `start_new_session=True` and correct label; interrupt path test verifies return code 130
  - Steps:
    - [x] Write test that patches `subprocess.Popen` in `isolate_mode` and asserts `start_new_session=True` and `ManagedSubprocess` used with `label="isolarium"`
    - [x] Convert `RealSubprocessRunner.run()` from `subprocess.run(cmd)` to `subprocess.Popen(cmd, start_new_session=True)` + `ManagedSubprocess` context manager
    - [x] Write test for interrupt path: when `managed.interrupted` is `True`, `run()` returns 130
    - [x] Implement interrupt detection and return 130
    - [x] Run full test suite to verify no regressions

- [x] **Task 4.2: Remove unused signal handling code from branch_lifecycle.py**
  - TaskType: REFACTOR
  - Entrypoint: `uv run --with pytest pytest tests/implement/`
  - Observable: No behavior change
  - Evidence: All existing tests continue to pass after dead code removal
  - Steps:
    - [x] Remove `_interrupt_state` module-level dict from `branch_lifecycle.py`
    - [x] Remove `register_signal_handlers()` function
    - [x] Remove `_handle_interrupt()` function
    - [x] Remove `cleanup_on_interrupt()` function
    - [x] Remove any imports that become unused after removal (e.g., `signal`, `sys`)
    - [x] Run full test suite to verify no regressions

---

## Change History
### 2026-02-20 18:03 - mark-task-complete
Implemented KeyboardInterrupt handling: __exit__ detects KeyboardInterrupt, calls process.terminate(), waits with timeout, joins threads with timeout, prints cleanup messages to stderr, sets interrupted=True, suppresses exception

### 2026-02-20 18:14 - mark-task-complete
Implemented SIGTSTP and SIGCONT forwarding to child process group with handler restoration on both exit paths

### 2026-02-20 18:22 - mark-task-complete
Integrated ManagedSubprocess into run_claude_with_output_capture: start_new_session=True on Popen, ManagedSubprocess context manager wraps process.wait(), early return with returncode=130 on interrupt

### 2026-02-20 18:26 - mark-step-complete
Test patches Popen and ManagedSubprocess, verifies start_new_session=True and label='isolarium'

### 2026-02-20 18:26 - mark-step-complete
RealSubprocessRunner.run() now uses Popen with start_new_session=True and ManagedSubprocess context manager

### 2026-02-20 18:27 - mark-step-complete
Interrupt path test verifies return code 130 when managed.interrupted is True

### 2026-02-20 18:27 - mark-step-complete
Interrupt detection returns 130 via managed.interrupted check

### 2026-02-20 18:27 - mark-step-complete
Full test suite: 404 passed (1 pre-existing integration error unrelated to changes)

### 2026-02-20 18:27 - mark-task-complete
RealSubprocessRunner uses Popen+ManagedSubprocess with start_new_session=True and returns 130 on interrupt

### 2026-02-20 18:32 - mark-task-complete
Removed _interrupt_state, register_signal_handlers(), _handle_interrupt(), cleanup_on_interrupt(), and unused signal/sys imports from branch_lifecycle.py. Removed corresponding TestInterruptHandling tests. 402 tests pass.
