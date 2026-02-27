"""Analyze Claude sessions: extract session IDs, correlate issues, invoke Claude."""

import os
import re
import sys
from datetime import datetime

from i2code.implement.claude_runner import ClaudeResult

_SESSION_PATTERN = re.compile(
    r"^session-\d{4}-\d{2}-\d{2}-\d{6}-(.+)\.md$"
)


def _extract_session_ids(sessions_dir: str) -> list[str]:
    """Extract session IDs from session filenames in the directory."""
    session_ids = set()
    for filename in os.listdir(sessions_dir):
        match = _SESSION_PATTERN.match(filename)
        if match:
            session_ids.add(match.group(1))
    return sorted(session_ids)


def _find_related_issues(issues_dir: str, session_ids: list[str]) -> list[str]:
    """Find issue files in issues/active/ that reference any session ID."""
    active_dir = os.path.join(issues_dir, "active")
    if not os.path.isdir(active_dir):
        return []

    related = []
    for filename in sorted(os.listdir(active_dir)):
        filepath = os.path.join(active_dir, filename)
        if not os.path.isfile(filepath):
            continue
        content = open(filepath).read()
        if any(sid in content for sid in session_ids):
            related.append(filepath)
    return related


def analyze_sessions(
    tracking_dir: str,
    claude_runner,
    template_renderer,
) -> ClaudeResult:
    """Analyze Claude sessions for patterns and improvements.

    Validates the tracking directory structure, extracts session IDs from
    filenames, finds related issue files, renders the analyze-sessions.md
    template, and invokes Claude non-interactively.

    Args:
        tracking_dir: Path to the project tracking directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If tracking_dir or sessions subdirectory does not exist
    """
    if not os.path.isdir(tracking_dir):
        print(f"Error: Project tracking directory not found: {tracking_dir}", file=sys.stderr)
        sys.exit(1)

    sessions_dir = os.path.join(tracking_dir, "sessions")
    if not os.path.isdir(sessions_dir):
        print(f"Error: Sessions directory not found: {sessions_dir}", file=sys.stderr)
        sys.exit(1)

    issues_dir = os.path.join(tracking_dir, "issues")

    session_ids = _extract_session_ids(sessions_dir)

    issues = ""
    if os.path.isdir(issues_dir) and session_ids:
        related_files = _find_related_issues(issues_dir, session_ids)
        issues = " ".join(related_files)

    report_file = os.path.join(
        tracking_dir,
        f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.adoc",
    )

    prompt = template_renderer("analyze-sessions.md", {
        "SESSIONS_DIR": sessions_dir,
        "ISSUES": issues,
        "REPORT_FILE": report_file,
    })

    cmd = [
        "claude",
        "--add-dir", sessions_dir,
        "--add-dir", issues_dir,
        "--allowedTools", "Read,Edit,Write",
        "-p", prompt,
    ]

    return claude_runner.run_batch(cmd, cwd=tracking_dir)
