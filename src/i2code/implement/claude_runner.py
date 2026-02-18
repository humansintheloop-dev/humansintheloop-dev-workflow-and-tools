"""ClaudeRunner: strategy pattern for running Claude commands.

Provides module-level run_claude_interactive() and run_claude_with_output_capture()
functions, plus ClaudeRunner classes (Real/Mock) that delegate to them.
"""

import json
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional


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

    process.wait()

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


class RealClaudeRunner:
    """Delegates to the module-level run functions."""

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_interactive(cmd, cwd=cwd)

    def run_with_capture(self, cmd: List[str], cwd: str) -> ClaudeResult:
        return run_claude_with_output_capture(cmd, cwd=cwd)


class MockClaudeRunner:
    """Wraps a mock shell script for integration testing.

    Both run_interactive() and run_with_capture() delegate to the mock script,
    which receives the original command as arguments.

    Args:
        script_path: Path to the mock shell script.
    """

    def __init__(self, script_path: str):
        self._script_path = script_path

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        result = subprocess.run(
            [self._script_path] + cmd,
            cwd=cwd,
        )
        return ClaudeResult(
            returncode=result.returncode,
            stdout="",
            stderr="",
        )

    def run_with_capture(self, cmd: List[str], cwd: str) -> ClaudeResult:
        result = subprocess.run(
            [self._script_path] + cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return ClaudeResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
