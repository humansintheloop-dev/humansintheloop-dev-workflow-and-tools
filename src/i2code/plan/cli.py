"""Plan command group: registers commands from handler modules."""

import click

from i2code.plan.plan_cli import register as register_plan_commands
from i2code.plan.task_cli import register as register_task_commands
from i2code.plan.thread_cli import register as register_thread_commands


@click.group()
def plan():
    """Plan file management commands."""
    pass


register_plan_commands(plan)
register_task_commands(plan)
register_thread_commands(plan)
