"""Generate daily summary reports for projects with today's sessions."""

import os
import sys
from datetime import datetime


def _today() -> str:
    """Return today's date as YYYY-MM-DD. Extracted for testability."""
    return datetime.now().strftime("%Y-%m-%d")


def _find_projects_with_sessions(tracking_dir: str, today: str, project_name: str | None) -> list[str]:
    """Find project directories that have session files from today."""
    if project_name:
        return _find_named_project(tracking_dir, today, project_name)
    return _discover_all_projects(tracking_dir, today)


def _find_named_project(tracking_dir: str, today: str, project_name: str) -> list[str]:
    """Validate and return a single named project if it has today's sessions."""
    project_dir = os.path.join(tracking_dir, project_name)
    if not os.path.isdir(project_dir):
        print(f"Error: Project not found: {project_name}", file=sys.stderr)
        sys.exit(1)
    if _project_has_sessions(project_dir, today):
        return [project_dir]
    return []


def _discover_all_projects(tracking_dir: str, today: str) -> list[str]:
    """Scan tracking_dir for all projects with today's sessions."""
    return [
        os.path.join(tracking_dir, entry)
        for entry in sorted(os.listdir(tracking_dir))
        if os.path.isdir(os.path.join(tracking_dir, entry))
        and _project_has_sessions(os.path.join(tracking_dir, entry), today)
    ]


def _project_has_sessions(project_dir: str, today: str) -> bool:
    """Check if a project directory has session files for the given date."""
    sessions_dir = os.path.join(project_dir, "sessions")
    return os.path.isdir(sessions_dir) and _has_sessions_for_date(sessions_dir, today)


def _has_sessions_for_date(sessions_dir: str, date: str) -> bool:
    """Check if a sessions directory has session files matching the given date."""
    prefix = f"session-{date}-"
    return any(f.startswith(prefix) and f.endswith(".md") for f in os.listdir(sessions_dir))


def _gather_session_files(sessions_dir: str, today: str) -> str:
    """Gather today's session filenames, sorted."""
    prefix = f"session-{today}-"
    files = sorted(
        os.path.join(sessions_dir, f)
        for f in os.listdir(sessions_dir)
        if f.startswith(prefix) and f.endswith(".md")
    )
    return "\n".join(files) if files else "No sessions found for today."


def _gather_issue_files(project_dir: str, today: str) -> str:
    """Gather today's issue filenames from issues/active/, sorted."""
    active_dir = os.path.join(project_dir, "issues", "active")
    if not os.path.isdir(active_dir):
        return "No issues filed today."
    prefix = f"{today}-"
    files = sorted(
        os.path.join(active_dir, f)
        for f in os.listdir(active_dir)
        if f.startswith(prefix) and f.endswith(".md")
    )
    return "\n".join(files) if files else "No issues filed today."


def create_summary_reports(
    tracking_dir: str,
    claude_runner,
    template_renderer,
    *,
    project_name: str | None = None,
) -> list[str]:
    """Generate summary reports for projects with today's sessions.

    Finds projects with sessions from today, renders the
    create-summary-report.md template per project, invokes Claude
    non-interactively with --print, and saves output to
    summary-reports/summary-<timestamp>.md.

    Args:
        tracking_dir: Path to the HITL tracking directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str
        project_name: Optional filter to a single project

    Returns:
        List of report file paths created

    Raises:
        SystemExit: If tracking_dir does not exist or project_name not found
    """
    if not os.path.isdir(tracking_dir):
        print(f"Error: HITL tracking directory not found: {tracking_dir}", file=sys.stderr)
        sys.exit(1)

    today = _today()
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")

    project_dirs = _find_projects_with_sessions(tracking_dir, today, project_name)
    if not project_dirs:
        return []

    report_paths = []
    for project_dir in project_dirs:
        name = os.path.basename(project_dir)
        sessions_dir = os.path.join(project_dir, "sessions")

        session_files = _gather_session_files(sessions_dir, today)
        issue_files = _gather_issue_files(project_dir, today)

        reports_dir = os.path.join(project_dir, "summary-reports")
        os.makedirs(reports_dir, exist_ok=True)

        report_file = os.path.join(reports_dir, f"summary-{timestamp}.md")

        prompt = template_renderer("create-summary-report.md", {
            "PROJECT_NAME": name,
            "SESSION_FILES": session_files,
            "ISSUE_FILES": issue_files,
        })

        cmd = [
            "claude",
            "--print",
            "--add-dir", project_dir,
            "--allowedTools", "Read",
            "-p", prompt,
        ]

        result = claude_runner.run_batch(cmd, cwd=project_dir)

        with open(report_file, "w") as f:
            f.write(result.output.stdout)

        report_paths.append(report_file)

    return report_paths
