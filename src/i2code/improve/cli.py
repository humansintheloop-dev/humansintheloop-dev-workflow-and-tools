"""Click commands for the improve workflow."""

import click

from i2code.script_command import script_command


@click.group("improve")
def improve():
    """Analyze sessions, review issues, and update configuration."""


script_command(
    improve,
    "analyze-sessions",
    "analyze-sessions.sh",
    "Analyze tracking sessions for patterns and improvements.",
)

script_command(
    improve,
    "summary-reports",
    "create-summary-reports.sh",
    "Create summary reports from HITL session data.",
)

script_command(
    improve,
    "review-issues",
    "review-issues.sh",
    "Review and triage active issues from HITL sessions.",
)

script_command(
    improve,
    "update-claude-files",
    "update-claude-files-from-project.sh",
    "Review project Claude files and update config-files templates.",
)
