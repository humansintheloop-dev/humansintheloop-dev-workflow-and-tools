"""Click commands for the idea workflow."""

import click

from i2code.script_command import script_command


@click.group("idea")
def idea():
    """Brainstorm and explore ideas."""


script_command(
    idea,
    "brainstorm",
    "brainstorm-idea.sh",
    "Brainstorm an idea.",
)
