"""Click commands for the spec workflow."""

import click

from i2code.script_command import script_command


@click.group("spec")
def spec():
    """Create and revise specifications."""


script_command(
    spec,
    "create",
    "make-spec.sh",
    "Create a specification from an idea.",
)

script_command(
    spec,
    "revise",
    "revise-spec.sh",
    "Revise an existing specification.",
)
