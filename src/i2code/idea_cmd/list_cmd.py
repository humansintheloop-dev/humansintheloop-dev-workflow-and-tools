"""Click command for listing ideas."""

from pathlib import Path

import click

from i2code.idea_resolver import list_ideas


def _format_idea_table(ideas):
    """Format ideas as aligned columnar output."""
    if not ideas:
        return ""
    name_width = max(len(idea.name) for idea in ideas)
    state_width = max(len(idea.state) for idea in ideas)
    lines = []
    for idea in ideas:
        lines.append(
            f"{idea.name:<{name_width}}  {idea.state:<{state_width}}  {idea.directory}"
        )
    return "\n".join(lines)


@click.command("list")
def idea_list():
    """List all ideas with their lifecycle state."""
    git_root = Path.cwd()
    ideas = list_ideas(git_root)
    output = _format_idea_table(ideas)
    if output:
        click.echo(output)
