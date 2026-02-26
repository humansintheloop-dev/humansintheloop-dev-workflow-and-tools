"""Click commands for the spec workflow."""

import click

from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.idea_project import IdeaProject
from i2code.spec_cmd.create_spec import create_spec
from i2code.spec_cmd.revise_spec import revise_spec


@click.group("spec")
def spec():
    """Create and revise specifications."""


@spec.command("create")
@click.argument("directory")
def spec_create(directory):
    """Create a specification from an idea."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    create_spec(project, claude_runner)


@spec.command("revise")
@click.argument("directory")
def spec_revise(directory):
    """Revise an existing specification."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    revise_spec(project, claude_runner)
