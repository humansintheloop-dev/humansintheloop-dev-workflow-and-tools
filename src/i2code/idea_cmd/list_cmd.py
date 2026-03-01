"""Click command for listing ideas."""

from pathlib import Path

import click

from i2code.idea.resolver import LIFECYCLE_STATES, list_ideas


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
@click.option(
    "--state",
    type=click.Choice(LIFECYCLE_STATES, case_sensitive=False),
    default=None,
    help="Filter ideas by lifecycle state.",
)
def idea_list(state):
    """List all ideas with their lifecycle state."""
    git_root = Path.cwd()
    ideas = list_ideas(git_root)
    if state:
        ideas = [idea for idea in ideas if idea.state == state]
    output = _format_idea_table(ideas)
    if output:
        click.echo(output)
