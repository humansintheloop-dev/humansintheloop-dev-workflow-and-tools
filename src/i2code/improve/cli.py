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
