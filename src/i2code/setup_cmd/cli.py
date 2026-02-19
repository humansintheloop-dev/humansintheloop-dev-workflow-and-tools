"""Click commands for the setup workflow."""

import click

from i2code.script_command import script_command


@click.group("setup")
def setup_group():
    """Initial project setup and configuration updates."""


script_command(
    setup_group,
    "claude-files",
    "setup-claude-files.sh",
    "Copy Claude configuration files into a project.",
)

script_command(
    setup_group,
    "update-project",
    "update-project-claude-files.sh",
    "Push template updates into a project's Claude files.",
)
