"""Click commands for managing HITL tracking directories."""

import os

import click

from i2code.tracking.manage import setup_tracking


@click.group("tracking")
def tracking():
    """Manage HITL tracking directories for session and issue recording."""


@tracking.command("setup")
@click.option("--link", "link_dir", metavar="DIR",
              help="Symlink .hitl/issues and .hitl/sessions to DIR/issues and DIR/sessions")
@click.option("--dry-run", is_flag=True,
              help="Show what would be done without making changes")
def setup_cmd(link_dir, dry_run):
    """Set up HITL tracking: migrate from .claude/ and optionally link to shared directory."""
    project_dir = os.getcwd()

    if dry_run:
        click.echo("Dry run (no changes will be made)\n")

    click.echo("Setting up HITL tracking...")
    target_link = os.path.abspath(link_dir) if link_dir else None
    setup_tracking(project_dir, target_link=target_link, dry_run=dry_run)

    click.echo("Done.")
