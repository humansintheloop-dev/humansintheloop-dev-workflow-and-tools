"""Click commands for the design workflow."""

import click

from i2code.design_cmd.create_design import create_design
from i2code.go_cmd.plugin_skills import list_plugin_skills
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.idea_project import IdeaProject


@click.group("design")
def design():
    """Create design documents."""


@design.command("create")
@click.argument("directory")
def design_create(directory):
    """Create a design document from a specification."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    create_design(project, claude_runner, plugin_skills_fn=list_plugin_skills)
