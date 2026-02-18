"""ClaudeRunner: strategy pattern for running Claude commands.

Provides ClaudeRunner as the base with run_interactive() and run_with_capture()
methods. MockClaudeRunner wraps mock shell scripts for integration testing.
"""

import subprocess
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


class RealClaudeRunner:
    """Delegates to the real run_claude_interactive / run_claude_with_output_capture."""

    def run_interactive(self, cmd: List[str], cwd: str) -> ClaudeResult:
        from i2code.implement.implement import run_claude_interactive
        return run_claude_interactive(cmd, cwd=cwd)

    def run_with_capture(self, cmd: List[str], cwd: str) -> ClaudeResult:
        from i2code.implement.implement import run_claude_with_output_capture
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
