"""Click command for archiving an idea."""

import subprocess
import sys
from pathlib import Path

import click

from i2code.idea.resolver import list_ideas, resolve_idea


def _git_commit(message: str, git_root: Path) -> None:
    """Create a git commit with the given message."""
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def _archive_one(name: str, git_root: Path) -> None:
    """Move a single idea from active/ to archived/ using git mv."""
    active_dir = git_root / "docs" / "ideas" / "active" / name
    archived_dir = git_root / "docs" / "ideas" / "archived" / name
    archived_dir.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "mv", str(active_dir), str(archived_dir)],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def _archive_named(name: str, git_root: Path, no_commit: bool) -> None:
    """Validate and archive a single idea by name."""
    try:
        resolve_idea(name, git_root)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    active_dir = git_root / "docs" / "ideas" / "active" / name
    if not active_dir.is_dir():
        click.echo(f"Idea '{name}' is already archived.", err=True)
        sys.exit(1)

    _archive_one(name, git_root)
    message = f"Archive idea {name}"
    if not no_commit:
        _git_commit(message, git_root)
    click.echo(message)


def _archive_completed(git_root: Path, no_commit: bool) -> None:
    """Archive all active ideas with state 'completed'."""
    ideas = list_ideas(git_root)
    completed_ideas = [
        idea for idea in ideas
        if idea.state == "completed"
        and (git_root / "docs" / "ideas" / "active" / idea.name).is_dir()
    ]
    if not completed_ideas:
        click.echo("No completed ideas to archive.")
        return

    for idea in completed_ideas:
        _archive_one(idea.name, git_root)
        click.echo(f"Archive idea {idea.name}")

    if not no_commit:
        names = ", ".join(idea.name for idea in completed_ideas)
        _git_commit(f"Archive completed ideas: {names}", git_root)


@click.command("archive")
@click.argument("name", required=False)
@click.option("--completed", is_flag=True, default=False, help="Archive all completed ideas.")
@click.option("--no-commit", is_flag=True, default=False, help="Stage changes but do not commit.")
def idea_archive(name, completed, no_commit):
    """Move an idea from active/ to archived/."""
    if not name and not completed:
        raise click.UsageError("Provide an idea name or use --completed.")
    git_root = Path.cwd()

    if completed:
        _archive_completed(git_root, no_commit)
    else:
        _archive_named(name, git_root, no_commit)


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
        _git_commit(message, git_root)

    click.echo(message)
