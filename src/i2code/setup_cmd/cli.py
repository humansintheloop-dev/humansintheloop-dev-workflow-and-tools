"""Click commands for the setup workflow."""

import sys

import click

from i2code.script_runner import run_script


@click.group("setup")
def setup_group():
    """Initial project setup and configuration updates."""


@setup_group.command("claude-files", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def claude_files_cmd(args):
    """Copy Claude configuration files into a project."""
    result = run_script("setup-claude-files.sh", args)
    sys.exit(result.returncode)
