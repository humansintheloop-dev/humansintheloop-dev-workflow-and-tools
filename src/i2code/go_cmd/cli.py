"""Click command for the go (orchestrator) workflow."""

import os
import sys

import click

from i2code.go_cmd.orchestrator import Orchestrator, OrchestratorDeps
from i2code.implement.idea_project import IdeaProject
from i2code.script_runner import run_script


@click.command("go")
@click.argument("directory")
def go_cmd(directory):
    """Run the idea-to-code orchestrator."""
    if not os.path.isdir(directory):
        click.echo(f"Directory does not exist: {directory}")
        click.echo("")
        if not click.confirm("Would you like to create it?", default=False):
            click.echo("Directory creation cancelled.")
            sys.exit(1)
        os.makedirs(directory, exist_ok=True)
        click.echo(f"Directory created successfully: {directory}")
        click.echo("")

    project = IdeaProject(directory)

    click.echo("================================================")
    click.echo("  Idea-to-Code Workflow Orchestrator")
    click.echo("================================================")
    click.echo("")
    click.echo(f"Working directory: {directory}")
    click.echo(f"Project name: {project.name}")
    click.echo("")

    deps = OrchestratorDeps(script_runner=run_script)
    orchestrator = Orchestrator(project, deps=deps)
    orchestrator.run()
