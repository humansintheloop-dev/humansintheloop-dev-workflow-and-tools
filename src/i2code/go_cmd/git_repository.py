"""Make sure an idea directory is inside a git repository before the workflow starts."""

import subprocess
import sys

import click

from i2code.go_cmd.orchestrator import git_root_from_path


def ensure_git_repository(directory):
    """Offer to run `git init` at the project root when the idea is not in a git repository."""
    if _is_inside_git_repository(directory):
        return
    project_root = git_root_from_path(directory)
    click.echo(f"{directory} is not in a git repository.")
    if not click.confirm(f"Run 'git init' in {project_root}?", default=False):
        sys.exit(1)
    subprocess.run(["git", "init"], cwd=str(project_root), check=True)


def _is_inside_git_repository(directory):
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(directory), capture_output=True, text=True,
    )
    return result.returncode == 0
