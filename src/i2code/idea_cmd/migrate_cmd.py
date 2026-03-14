"""Migrate ideas from directory-based state to metadata files."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

from i2code.idea.metadata import write_metadata

LEGACY_STATES = ("draft", "ready", "wip", "completed", "abandoned")
IDEAS_DIR = os.path.join("docs", "ideas")
COMMIT_MESSAGE = "Migrate ideas from directory-based state to metadata files"


def _find_git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True, capture_output=True, text=True,
    )
    return Path(result.stdout.strip())


def _ideas_in_state_dir(state: str, state_dir: Path) -> list[tuple[str, str, Path]]:
    return [
        (entry, state, state_dir / entry)
        for entry in sorted(os.listdir(state_dir))
        if (state_dir / entry).is_dir()
    ]


def _discover_legacy_ideas(git_root: Path) -> list[tuple[str, str, Path]]:
    ideas: list[tuple[str, str, Path]] = []
    for state in LEGACY_STATES:
        state_dir = git_root / IDEAS_DIR / state
        if state_dir.is_dir():
            ideas.extend(_ideas_in_state_dir(state, state_dir))
    return ideas


def _move_idea_directory(old_path: Path, new_path: Path, git_root: Path) -> None:
    result = subprocess.run(
        ["git", "mv", str(old_path), str(new_path)],
        cwd=str(git_root), capture_output=True,
    )
    if result.returncode != 0:
        shutil.move(str(old_path), str(new_path))
        subprocess.run(
            ["git", "add", str(new_path)],
            cwd=str(git_root), check=True, capture_output=True,
        )


def _migrate_idea(idea: tuple[str, str, Path], active_dir: Path, git_root: Path) -> None:
    name, state, old_path = idea
    new_path = active_dir / name
    _move_idea_directory(old_path, new_path, git_root)
    metadata_path = new_path / f"{name}-metadata.yaml"
    write_metadata(metadata_path, {"state": state})
    subprocess.run(
        ["git", "add", str(metadata_path)],
        cwd=str(git_root), check=True, capture_output=True,
    )


def _remove_legacy_state_dirs(git_root: Path) -> None:
    for state in LEGACY_STATES:
        state_dir = git_root / IDEAS_DIR / state
        if state_dir.is_dir():
            shutil.rmtree(state_dir)


def _git_commit(git_root: Path) -> None:
    result = subprocess.run(
        ["git", "commit", "-m", COMMIT_MESSAGE],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"Commit failed: {result.stderr}", err=True)
        sys.exit(1)


@click.command("migrate")
@click.option("--no-commit", is_flag=True, help="Stage changes without committing.")
def idea_migrate(no_commit: bool) -> None:
    """Migrate ideas from directory-based state to metadata files."""
    try:
        git_root = _find_git_root()
    except subprocess.CalledProcessError:
        click.echo("Not a git repository.", err=True)
        sys.exit(1)

    legacy_ideas = _discover_legacy_ideas(git_root)
    if not legacy_ideas:
        click.echo("Nothing to migrate — no old-style ideas found.")
        return

    active_dir = git_root / IDEAS_DIR / "active"
    active_dir.mkdir(parents=True, exist_ok=True)

    for idea in legacy_ideas:
        _migrate_idea(idea, active_dir, git_root)

    _remove_legacy_state_dirs(git_root)
    click.echo(f"Migrated {len(legacy_ideas)} idea(s) to active/.")

    if not no_commit:
        _git_commit(git_root)
