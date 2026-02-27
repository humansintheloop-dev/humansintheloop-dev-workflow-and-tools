"""Review active GitHub issues from HITL tracking directory."""

import os
import sys
from datetime import datetime


def _current_year() -> str:
    """Return the current year as YYYY. Extracted for testability."""
    return datetime.now().strftime("%Y")


def _find_active_issue_files(search_path: str, year: str) -> list[str]:
    """Find issue files in issues/active/ matching the current year.

    Walks the search_path looking for files matching
    ``*/issues/active/<year>-*.md`` and excludes files that contain
    a ``type: unknown`` line.
    """
    results = []
    for dirpath, _dirnames, filenames in os.walk(search_path):
        if not dirpath.endswith(os.path.join("issues", "active")):
            continue
        for filename in sorted(filenames):
            if not filename.startswith(f"{year}-") or not filename.endswith(".md"):
                continue
            filepath = os.path.join(dirpath, filename)
            if _is_type_unknown(filepath):
                continue
            results.append(filepath)
    return sorted(results)


def _is_type_unknown(filepath: str) -> bool:
    """Check if a file contains a 'type: unknown' line."""
    with open(filepath) as f:
        for line in f:
            if line.rstrip() == "type: unknown":
                return True
    return False


def _create_resolved_dirs(issue_files: list[str]) -> None:
    """Create resolved/ directories alongside active/ for each issue's project."""
    seen = set()
    for issue_path in issue_files:
        # issue_path is .../issues/active/filename.md
        active_dir = os.path.dirname(issue_path)
        issues_dir = os.path.dirname(active_dir)
        resolved_dir = os.path.join(issues_dir, "resolved")
        if resolved_dir not in seen:
            os.makedirs(resolved_dir, exist_ok=True)
            seen.add(resolved_dir)


def review_issues(
    tracking_dir: str,
    claude_runner,
    template_renderer,
    *,
    project: str | None = None,
):
    """Review active issues and invoke Claude interactively.

    Finds active issue files from the current year, excludes those
    marked ``type: unknown``, creates ``resolved/`` directories, renders
    the ``review-issues.md`` template, and invokes Claude interactively.

    Args:
        tracking_dir: Path to the HITL tracking directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str
        project: Optional project subdirectory to restrict scope

    Returns:
        ClaudeResult from Claude invocation, or None if no active issues

    Raises:
        SystemExit: If tracking_dir or project subdirectory does not exist
    """
    if not os.path.isdir(tracking_dir):
        print(f"Error: HITL tracking directory not found: {tracking_dir}", file=sys.stderr)
        sys.exit(1)

    if project:
        search_path = os.path.join(tracking_dir, project)
        if not os.path.isdir(search_path):
            print(f"Error: Project directory not found: {search_path}", file=sys.stderr)
            sys.exit(1)
    else:
        search_path = tracking_dir

    year = _current_year()
    active_issues = _find_active_issue_files(search_path, year)

    if not active_issues:
        print(f"No active issues found for {year} (excluding type: unknown)")
        return None

    print("Found active issues:")
    print(" ".join(active_issues))
    print()

    _create_resolved_dirs(active_issues)

    active_issues_str = " ".join(active_issues)

    prompt = template_renderer("review-issues.md", {
        "ACTIVE_ISSUES": active_issues_str,
        "HITL_TRACKING_DIR": tracking_dir,
    })

    cmd = ["claude", prompt]

    return claude_runner.run_interactive(cmd, cwd=tracking_dir)
