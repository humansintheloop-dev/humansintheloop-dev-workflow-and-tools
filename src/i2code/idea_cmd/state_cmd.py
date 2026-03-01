"""Click command for displaying idea lifecycle state."""

import sys
from pathlib import Path

import click

from i2code.idea_resolver import list_ideas, resolve_idea, state_from_path


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
        return state_from_path(path)
    return resolve_idea(name_or_path, Path.cwd()).state


@click.command("state")
@click.argument("name_or_path", shell_complete=_complete_name_or_path)
def idea_state(name_or_path):
    """Display the lifecycle state of an idea."""
    try:
        state = _resolve_state(name_or_path)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(state)
