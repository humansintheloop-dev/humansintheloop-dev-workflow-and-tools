"""Click command for displaying and transitioning idea lifecycle state."""

import subprocess
import sys
from pathlib import Path

import click

from i2code.idea.metadata import read_metadata, write_metadata
from i2code.idea_cmd.transition_rules import validate_transition
from i2code.idea.resolver import LIFECYCLE_STATES, list_ideas, resolve_idea


def _complete_name_or_path(ctx, _param, incomplete):
    """Offer both idea names and filesystem paths for shell completion."""
    completions = []
    try:
        git_root = Path.cwd()
        for idea in list_ideas(git_root):
            if idea.name.startswith(incomplete):
                completions.append(idea.name)
    except Exception:
        pass
    return completions


def _resolve_state(name_or_path):
    """Resolve lifecycle state from a name or directory path."""
    path = Path(name_or_path)
    if path.is_dir():
        name = path.name
        return resolve_idea(name, Path.cwd()).state
    return resolve_idea(name_or_path, Path.cwd()).state


def execute_transition(name, old_path, new_state, git_root):
    """Update an idea's state in its metadata file and commit.

    Returns a message string on success.
    Raises RuntimeError with the git error on failure.
    """
    old_state = resolve_idea(name, git_root).state
    if old_state == new_state:
        return f"Idea {name} is already in state {new_state}"
    metadata_path = Path(old_path) / f"{name}-metadata.yaml"
    metadata = read_metadata(metadata_path)
    metadata["state"] = new_state
    write_metadata(metadata_path, metadata)
    result = subprocess.run(
        ["git", "add", str(metadata_path)],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        msg = result.stderr.strip()
        raise RuntimeError(msg)
    commit_message = f"Move idea {name} from {old_state} to {new_state}"
    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        msg = result.stderr.strip()
        raise RuntimeError(msg)
    return commit_message


@click.command("state")
@click.argument("name_or_path", shell_complete=_complete_name_or_path)
@click.argument(
    "new_state",
    required=False,
    default=None,
    type=click.Choice(LIFECYCLE_STATES, case_sensitive=False),
)
@click.option("--force", is_flag=True, default=False, help="Bypass transition rules.")
def idea_state(name_or_path, new_state, force):  # noqa: FBT002
    """Display or transition the lifecycle state of an idea."""
    try:
        if new_state is None:
            state = _resolve_state(name_or_path)
            click.echo(state)
        else:
            git_root = Path.cwd()
            idea = resolve_idea(name_or_path, git_root)
            idea_dir = git_root / idea.directory
            if not force:
                violation = validate_transition(idea.state, new_state, idea_dir)
                if violation:
                    click.echo(f"{violation}. Use --force to override.", err=True)
                    sys.exit(1)
            message = execute_transition(idea.name, idea_dir, new_state, git_root)
            click.echo(message)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
