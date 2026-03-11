"""Click command for archiving an idea."""

import subprocess
import sys
from pathlib import Path

import click

from i2code.idea.resolver import resolve_idea


@click.command("archive")
@click.argument("name")
@click.option("--no-commit", is_flag=True, default=False, help="Stage changes but do not commit.")
def idea_archive(name, no_commit):
    """Move an idea from active/ to archived/."""
    git_root = Path.cwd()
    try:
        resolve_idea(name, git_root)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    active_dir = git_root / "docs" / "ideas" / "active" / name
    archived_dir = git_root / "docs" / "ideas" / "archived" / name

    if not active_dir.is_dir():
        click.echo(f"Idea '{name}' is already archived.", err=True)
        sys.exit(1)

    archived_dir.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "mv", str(active_dir), str(archived_dir)],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    message = f"Archive idea {name}"
    if not no_commit:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(git_root), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    click.echo(message)


@click.command("unarchive")
@click.argument("name")
@click.option("--no-commit", is_flag=True, default=False, help="Stage changes but do not commit.")
def idea_unarchive(name, no_commit):
    """Move an idea from archived/ to active/."""
    git_root = Path.cwd()
    try:
        resolve_idea(name, git_root)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    archived_dir = git_root / "docs" / "ideas" / "archived" / name
    active_dir = git_root / "docs" / "ideas" / "active" / name

    if not archived_dir.is_dir():
        click.echo(f"Idea '{name}' is already active.", err=True)
        sys.exit(1)

    active_dir.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "mv", str(archived_dir), str(active_dir)],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    message = f"Unarchive idea {name}"
    if not no_commit:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(git_root), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())

    click.echo(message)
