"""Click command for managing HITL tracking directories."""

import os

import click

from i2code.tracking.manage import migrate, link


@click.command("manage-tracking")
@click.option("--migrate", "do_migrate", is_flag=True,
              help="Move .claude/issues and .claude/sessions to .hitl/, update .gitignore")
@click.option("--link", "link_dir", metavar="DIR",
              help="Symlink .hitl/issues and .hitl/sessions to DIR/issues and DIR/sessions")
@click.option("--dry-run", is_flag=True,
              help="Show what would be done without making changes")
def manage_tracking_cmd(do_migrate, link_dir, dry_run):
    """Manage HITL tracking directories for session and issue recording."""
    if not do_migrate and not link_dir:
        raise click.UsageError("Specify --migrate and/or --link DIR")

    project_dir = os.getcwd()

    if dry_run:
        click.echo("Dry run (no changes will be made)\n")

    if do_migrate:
        click.echo("Migrating .claude/{issues,sessions} -> .hitl/...")
        migrate(project_dir, dry_run=dry_run)
        click.echo()

    if link_dir:
        link_dir = os.path.abspath(link_dir)
        click.echo(f"Linking .hitl/{{issues,sessions}} -> {link_dir}/...")
        link(project_dir, link_dir, dry_run=dry_run)
        click.echo()

    click.echo("Done.")
