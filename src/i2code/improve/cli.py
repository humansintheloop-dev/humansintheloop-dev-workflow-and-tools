"""Click commands for the improve workflow."""

import sys

import click

from i2code.script_runner import run_script


@click.group("improve")
def improve():
    """Analyze sessions, review issues, and update configuration."""


@improve.command("analyze-sessions", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def analyze_sessions_cmd(args):
    """Analyze tracking sessions for patterns and improvements."""
    result = run_script("analyze-sessions.sh", args)
    sys.exit(result.returncode)


@improve.command("summary-reports", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def summary_reports_cmd(args):
    """Create summary reports from HITL session data."""
    result = run_script("create-summary-reports.sh", args)
    sys.exit(result.returncode)


@improve.command("review-issues", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def review_issues_cmd(args):
    """Review and triage active issues from HITL sessions."""
    result = run_script("review-issues.sh", args)
    sys.exit(result.returncode)


@improve.command(
    "update-claude-files", context_settings={"ignore_unknown_options": True}
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def update_claude_files_cmd(args):
    """Review project Claude files and update config-files templates."""
    result = run_script("update-claude-files-from-project.sh", args)
    sys.exit(result.returncode)
