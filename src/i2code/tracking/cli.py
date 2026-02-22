"""Click commands for managing HITL tracking directories."""

import os

import click

from i2code.tracking.manage import migrate_tracking, link_tracking
from i2code.tracking.model import TrackedWorkingDirectory


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
    twd = TrackedWorkingDirectory.scan(project_dir)

    if dry_run:
        click.echo("Dry run (no changes will be made)\n")

    click.echo("Migrating .claude/{issues,sessions} -> .hitl/...")
    migrate_tracking(twd, dry_run=dry_run)
    click.echo()

    if link_dir:
        link_dir = os.path.abspath(link_dir)
        click.echo(f"Linking .hitl/{{issues,sessions}} -> {link_dir}/...")
        link_tracking(project_dir, link_dir, dry_run=dry_run)
        click.echo()

    click.echo("Done.")
