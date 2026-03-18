"""Click group and commands for issue management."""

import os
import sys

import click

from i2code.issue.create import create_issue


@click.group("issue")
def issue():
    """Manage issue reports."""


@issue.command("create")
@click.option("--session-id", default="unknown", help="Claude session ID")
def issue_create(session_id):
    """Create an issue report from JSON on stdin."""
    project_root = os.environ.get("I2CODE_PROJECT_ROOT", os.getcwd())
    target_dir = os.path.join(project_root, ".hitl", "issues", "active")

    json_str = click.get_text_stream("stdin").read()

    try:
        path = create_issue(json_str, session_id, target_dir)
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(path)
