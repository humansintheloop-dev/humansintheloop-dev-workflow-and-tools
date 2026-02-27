"""Click commands for the improve workflow."""

import click

from i2code.implement.claude_runner import ClaudeRunner
from i2code.improve.analyze_sessions import analyze_sessions
from i2code.improve.review_issues import review_issues
from i2code.improve.summary_reports import create_summary_reports
from i2code.improve.update_claude_files import update_claude_files
from i2code.template_renderer import render_template


@click.group("improve")
def improve():
    """Analyze sessions, review issues, and update configuration."""


@improve.command("analyze-sessions")
@click.argument("tracking_dir")
def analyze_sessions_cmd(tracking_dir):
    """Analyze tracking sessions for patterns and improvements."""
    claude_runner = ClaudeRunner()
    analyze_sessions(tracking_dir, claude_runner, render_template)


@improve.command("summary-reports")
@click.argument("tracking_dir")
@click.option("--project-name", default=None, help="Restrict to a single project.")
def summary_reports_cmd(tracking_dir, project_name):
    """Create summary reports from HITL session data."""
    claude_runner = ClaudeRunner()
    create_summary_reports(
        tracking_dir, claude_runner, render_template, project_name=project_name
    )


@improve.command("review-issues")
@click.argument("tracking_dir")
@click.option("--project", default=None, help="Restrict to issues in a project subdirectory.")
def review_issues_cmd(tracking_dir, project):
    """Review and triage active issues from HITL sessions."""
    claude_runner = ClaudeRunner()
    review_issues(tracking_dir, claude_runner, render_template, project=project)


@improve.command("update-claude-files")
@click.argument("project_dir")
@click.option("--config-dir", required=True, help="Path to the config-files directory.")
def update_claude_files_cmd(project_dir, config_dir):
    """Review project Claude files and update config-files templates."""
    claude_runner = ClaudeRunner()
    update_claude_files(project_dir, config_dir, claude_runner, render_template)
