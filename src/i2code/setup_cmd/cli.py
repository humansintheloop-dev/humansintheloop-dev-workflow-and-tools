"""Click commands for the setup workflow."""

import click

from i2code.implement.claude_runner import ClaudeRunner
from i2code.setup_cmd.claude_files import setup_claude_files
from i2code.setup_cmd.update_project import update_project
from i2code.template_renderer import render_template


@click.group("setup")
def setup_group():
    """Initial project setup and configuration updates."""


@setup_group.command("claude-files")
@click.option("--config-dir", required=True, help="Path to the config-files directory.")
def claude_files_cmd(config_dir):
    """Copy Claude configuration files into a project."""
    setup_claude_files(config_dir)


@setup_group.command("update-project")
@click.argument("project_dir")
@click.option("--config-dir", required=True, help="Path to the config-files directory.")
def update_project_cmd(project_dir, config_dir):
    """Push template updates into a project's Claude files."""
    claude_runner = ClaudeRunner()
    update_project(project_dir, config_dir, claude_runner, render_template)
