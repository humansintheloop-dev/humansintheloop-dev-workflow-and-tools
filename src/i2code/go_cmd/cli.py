"""Click command for the go (orchestrator) workflow."""

import os
import sys
from pathlib import Path

import click

from i2code.go_cmd.orchestrator import Orchestrator, OrchestratorDeps
from i2code.idea_resolver import list_ideas, resolve_idea
from i2code.implement.idea_project import IdeaProject


def _complete_name_or_path(ctx, _param, incomplete):
    """Offer idea names for shell completion."""
    completions = []
    try:
        git_root = Path.cwd()
        for idea in list_ideas(git_root):
            if idea.name.startswith(incomplete):
                completions.append(idea.name)
    except Exception:
        pass
    return completions


def _resolve_directory(argument):
    """Resolve a directory argument that may be a path or an idea name.

    Returns the directory path string.
    Raises SystemExit on resolution errors.
    """
    if os.path.isdir(argument):
        return argument
    if os.sep in argument or argument.startswith("."):
        return None
    try:
        git_root = Path.cwd()
        idea = resolve_idea(argument, git_root)
        return str(git_root / idea.directory)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)


@click.command("go")
@click.argument("directory", shell_complete=_complete_name_or_path)
def go_cmd(directory):
    """Run the idea-to-code orchestrator."""
    resolved = _resolve_directory(directory)
    if resolved is not None:
        directory = resolved
    elif not os.path.isdir(directory):
        click.echo(f"Directory does not exist: {directory}")
        click.echo("")
        if not click.confirm("Would you like to create it?", default=False):
            click.echo("Directory creation cancelled.")
            sys.exit(1)
        os.makedirs(directory, exist_ok=True)
        click.echo(f"Directory created successfully: {directory}")
        click.echo("")

    project = IdeaProject(directory)

    click.echo("================================================")
    click.echo("  Idea-to-Code Workflow Orchestrator")
    click.echo("================================================")
    click.echo("")
    click.echo(f"Working directory: {directory}")
    click.echo(f"Project name: {project.name}")
    click.echo("")

    deps = OrchestratorDeps()
    orchestrator = Orchestrator(project, deps=deps)
    orchestrator.run()
