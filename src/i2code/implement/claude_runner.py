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
from typing import Any, Dict, List, Optional

from i2code.implement.managed_subprocess import ManagedSubprocess


class ClaudeResult:
    """Result of running Claude with output capture."""

    def __init__(self, returncode: int, stdout: str, stderr: str,
                 permission_denials: Optional[List[Dict[str, Any]]] = None,
                 error_message: Optional[str] = None,
                 last_messages: Optional[List[Dict[str, Any]]] = None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.permission_denials = permission_denials or []
        self.error_message = error_message
        self.last_messages = last_messages or []


def run_claude_interactive(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command interactively, inheriting terminal.

    In interactive mode, Claude needs direct access to the terminal
    for its TUI, so we don't capture stdout/stderr.
    """
    result = subprocess.run(cmd, cwd=cwd)

    return ClaudeResult(
        returncode=result.returncode,
        stdout="",
        stderr="",
        permission_denials=[],
        error_message=None,
        last_messages=[],
    )


def run_claude_with_output_capture(cmd: List[str], cwd: str) -> ClaudeResult:
    """Run Claude command, capturing output while displaying progress.

    For stream-json output, prints a dot for each JSON message received.
    At the end, parses the result to check for errors and permission denials.
    """
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    stdout_chunks: List[str] = []
    stderr_chunks: List[str] = []

    def read_stdout_stream_json(pipe, chunks: List[str]):
        buffer = ""
        while True:
            chunk = pipe.read1(4096) if hasattr(pipe, 'read1') else pipe.read(4096)
            if not chunk:
                break
            text = chunk.decode('utf-8', errors='replace')
            chunks.append(text)
            buffer += text

            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    sys.stdout.write('.')
                    sys.stdout.flush()

    def read_stderr(pipe, chunks: List[str]):
        while True:
            chunk = pipe.read1(4096) if hasattr(pipe, 'read1') else pipe.read(4096)
            if not chunk:
                break
            text = chunk.decode('utf-8', errors='replace')
            chunks.append(text)
            sys.stderr.write(text)
            sys.stderr.flush()

    stdout_thread = threading.Thread(
        target=read_stdout_stream_json,
        args=(process.stdout, stdout_chunks),
    )
    stderr_thread = threading.Thread(
        target=read_stderr,
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
            stdout=''.join(stdout_chunks),
            stderr=''.join(stderr_chunks),
        )

    stdout_thread.join()
    stderr_thread.join()

    sys.stdout.write('\n')
    sys.stdout.flush()

    full_stdout = ''.join(stdout_chunks)
    permission_denials = []
    error_message = None
    all_messages: List[Dict[str, Any]] = []

    for line in full_stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            all_messages.append(msg)
            if msg.get('type') == 'result':
                permission_denials = msg.get('permission_denials', [])
                if msg.get('is_error'):
                    error_message = msg.get('result', 'Unknown error')
                elif permission_denials:
                    error_message = f"Permission denied for {len(permission_denials)} action(s)"
        except json.JSONDecodeError:
            continue

    last_messages = all_messages[-5:] if all_messages else []

    return ClaudeResult(
        returncode=process.returncode,
        stdout=full_stdout,
        stderr=''.join(stderr_chunks),
        permission_denials=permission_denials,
        error_message=error_message,
        last_messages=last_messages,
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

    if claude_result.permission_denials:
        _format_permission_denials(claude_result.permission_denials)

    if claude_result.error_message:
        print(f"\nClaude error: {claude_result.error_message}", file=sys.stderr)

    if claude_result.last_messages:
        print(f"\nLast {len(claude_result.last_messages)} messages from Claude:", file=sys.stderr)
        for msg in claude_result.last_messages:
            _format_message(msg)


class ClaudeRunner:
    """Delegates to the module-level run functions."""

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_interactive(cmd, cwd=cwd)

    def run_with_capture(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_with_output_capture(cmd, cwd=cwd)
