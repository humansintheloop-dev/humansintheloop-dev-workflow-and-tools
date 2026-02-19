"""Click commands for the design workflow."""

import click

from i2code.script_command import script_command


@click.group("design")
def design():
    """Create design documents."""


script_command(
    design,
    "create",
    "create-design-doc.sh",
    "Create a design document from a specification.",
)
