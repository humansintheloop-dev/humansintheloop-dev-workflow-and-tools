"""Plan command group: registers commands from handler modules."""

import click

from i2code.go_cmd.create_plan import PlanServices, create_plan
from i2code.go_cmd.plan_validator import validate_plan
from i2code.go_cmd.plugin_skills import list_plugin_skills
from i2code.go_cmd.revise_plan import revise_plan
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.idea_project import IdeaProject
from i2code.plan.plan_cli import register as register_plan_commands
from i2code.plan.task_cli import register as register_task_commands
from i2code.plan.thread_cli import register as register_thread_commands
from i2code.template_renderer import render_template


@click.group()
def plan():
    """Plan file management commands."""
    pass


register_plan_commands(plan)
register_task_commands(plan)
register_thread_commands(plan)


@plan.command("create")
@click.argument("directory")
def plan_create(directory):
    """Create an implementation plan from a specification."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    services = PlanServices(
        template_renderer=render_template,
        plugin_skills_fn=list_plugin_skills,
        validator_fn=validate_plan,
    )
    create_plan(project, claude_runner, services)


@plan.command("revise")
@click.argument("directory")
def plan_revise(directory):
    """Revise an existing implementation plan."""
    project = IdeaProject(directory)
    claude_runner = ClaudeRunner()
    revise_plan(project, claude_runner, render_template)
