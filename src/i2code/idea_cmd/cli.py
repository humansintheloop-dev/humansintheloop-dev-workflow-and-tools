"""Click commands for the idea workflow."""

import click

from i2code.idea_cmd.brainstorm import brainstorm_idea
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.idea_project import IdeaProject


@click.group("idea")
def idea():
    """Brainstorm and explore ideas."""


@idea.command("brainstorm")
@click.argument("directory")
def idea_brainstorm(directory):
    """Brainstorm an idea."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    brainstorm_idea(project, claude_runner)
