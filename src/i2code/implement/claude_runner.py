"""ClaudeRunner: strategy pattern for running Claude commands.

Provides module-level run_claude_interactive() and run_claude_with_output_capture()
functions, plus ClaudeRunner classes (Real/Mock) that delegate to them.
Also includes result diagnostics: check_claude_success() and
print_task_failure_diagnostics().
"""

import json
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from i2code.implement.managed_subprocess import ManagedSubprocess


@dataclass
class CapturedOutput:
    """Captured stdout and stderr from a Claude process."""
    stdout: str = ""
    stderr: str = ""


@dataclass
class DiagnosticInfo:
    """Parsed diagnostic details from stream-json output."""
    permission_denials: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    last_messages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ClaudeResult:
    """Result of running Claude with output capture."""
    returncode: int
    output: CapturedOutput = field(default_factory=CapturedOutput)
    diagnostics: DiagnosticInfo = field(default_factory=DiagnosticInfo)


def run_claude_interactive(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command interactively, inheriting terminal.

    In interactive mode, Claude needs direct access to the terminal
    for its TUI, so we don't capture stdout/stderr.
    """
    result = subprocess.run(cmd, cwd=cwd)

    return ClaudeResult(returncode=result.returncode)


def _print_dot_per_line(buffer: str) -> str:
    """Print a progress dot for each complete line and return the remainder."""
    while '\n' in buffer:
        line, buffer = buffer.split('\n', 1)
        if line.strip():
            sys.stdout.write('.')
            sys.stdout.flush()
    return buffer


def _read_pipe_chunks(pipe, chunks: List[str]):
    """Read and decode pipe chunks, accumulating into chunks list."""
    while True:
        chunk = pipe.read1(4096) if hasattr(pipe, 'read1') else pipe.read(4096)
        if not chunk:
            break
        text = chunk.decode('utf-8', errors='replace')
        chunks.append(text)
        yield text


def _read_pipe_with_progress(pipe, chunks: List[str]):
    """Read stdout pipe, printing a dot for each JSON message."""
    buffer = ""
    for text in _read_pipe_chunks(pipe, chunks):
        buffer = _print_dot_per_line(buffer + text)


def _read_pipe_to_stderr(pipe, chunks: List[str]):
    """Read stderr pipe, forwarding output to stderr."""
    for text in _read_pipe_chunks(pipe, chunks):
        sys.stderr.write(text)
        sys.stderr.flush()


def _extract_result_from_message(msg: Dict[str, Any]):
    """Extract permission denials and error from a result message.

    Returns (permission_denials, error_message).
    """
    permission_denials = msg.get('permission_denials', [])
    if msg.get('is_error'):
        return permission_denials, msg.get('result', 'Unknown error')
    if permission_denials:
        return permission_denials, f"Permission denied for {len(permission_denials)} action(s)"
    return permission_denials, None


def _parse_stream_json_output(full_stdout: str) -> DiagnosticInfo:
    """Parse stream-json output for errors and permission denials."""
    permission_denials: List[Dict[str, Any]] = []
    error_message = None
    all_messages: List[Dict[str, Any]] = []

    for line in full_stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        all_messages.append(msg)
        if msg.get('type') == 'result':
            permission_denials, error_message = _extract_result_from_message(msg)

    last_messages = all_messages[-5:] if all_messages else []
    return DiagnosticInfo(
        permission_denials=permission_denials,
        error_message=error_message,
        last_messages=last_messages,
    )


def run_claude_with_output_capture(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command, capturing output while displaying progress.

    For stream-json output, prints a dot for each JSON message received.
    At the end, parses the result to check for errors and permission denials.
    """
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    stdout_chunks: List[str] = []
    stderr_chunks: List[str] = []

    stdout_thread = threading.Thread(
        target=_read_pipe_with_progress,
        args=(process.stdout, stdout_chunks),
    )
    stderr_thread = threading.Thread(
        target=_read_pipe_to_stderr,
        args=(process.stderr, stderr_chunks),
    )

    stdout_thread.start()
    stderr_thread.start()

    with ManagedSubprocess(
        process=process,
        label="claude",
        threads=[stdout_thread, stderr_thread],
    ) as managed:
        process.wait()

    if managed.interrupted:
        return ClaudeResult(
            returncode=130,
            output=CapturedOutput(''.join(stdout_chunks), ''.join(stderr_chunks)),
        )

    stdout_thread.join()
    stderr_thread.join()

    sys.stdout.write('\n')
    sys.stdout.flush()

    full_stdout = ''.join(stdout_chunks)

    return ClaudeResult(
        returncode=process.returncode,
        output=CapturedOutput(full_stdout, ''.join(stderr_chunks)),
        diagnostics=_parse_stream_json_output(full_stdout),
    )


def check_claude_success(exit_code: int, head_before: str, head_after: str) -> bool:
    """Check if Claude invocation was successful.

    Success requires:
    1. Exit code of 0
    2. HEAD advanced (a commit was made)
    """
    return exit_code == 0 and head_before != head_after


def _format_permission_denials(denials) -> None:
    print(f"\nPermission denied for {len(denials)} action(s):", file=sys.stderr)
    for denial in denials:
        tool_name = denial.get('tool_name', 'Unknown')
        tool_input = denial.get('tool_input', {})
        cmd = tool_input.get('command', tool_input.get('description', 'N/A'))
        print(f"  - {tool_name}: {cmd}", file=sys.stderr)
    print("\nAdd missing permissions to .claude/settings.local.json", file=sys.stderr)


def _format_message(msg) -> None:
    msg_type = msg.get('type', 'unknown')
    if msg_type == 'assistant':
        for item in msg.get('message', {}).get('content', []):
            if item.get('type') == 'text':
                print(f"  [assistant] {item.get('text', '')[:200]}...", file=sys.stderr)
    elif msg_type == 'result':
        print(f"  [result] {msg.get('result', '')[:200]}...", file=sys.stderr)
    else:
        print(f"  [{msg_type}]", file=sys.stderr)


def print_task_failure_diagnostics(
    claude_result,
    head_before: str,
    head_after: str,
) -> None:
    """Print diagnostic information when a Claude task execution fails."""
    print("\nError: Task execution failed.", file=sys.stderr)
    print(f"  Exit code: {claude_result.returncode}", file=sys.stderr)
    print(f"  HEAD before: {head_before}", file=sys.stderr)
    print(f"  HEAD after: {head_after}", file=sys.stderr)

    if claude_result.diagnostics.permission_denials:
        _format_permission_denials(claude_result.diagnostics.permission_denials)

    if claude_result.diagnostics.error_message:
        print(f"\nClaude error: {claude_result.diagnostics.error_message}", file=sys.stderr)

    if claude_result.diagnostics.last_messages:
        print(f"\nLast {len(claude_result.diagnostics.last_messages)} messages from Claude:", file=sys.stderr)
        for msg in claude_result.diagnostics.last_messages:
            _format_message(msg)


class ClaudeRunner:
    """Delegates to the module-level run functions."""

    def __init__(self, interactive: bool = True):
        self._interactive = interactive

    def run(self, cmd: List[str], cwd: str) -> ClaudeResult:
        if self._interactive:
            return self.run_interactive(cmd, cwd=cwd)
        return self.run_batch(cmd, cwd=cwd)

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_interactive(cmd, cwd=cwd)

    def run_batch(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_with_output_capture(cmd, cwd=cwd)
