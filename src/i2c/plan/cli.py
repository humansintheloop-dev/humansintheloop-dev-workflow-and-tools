"""Plan command group: registers commands from handler modules."""

import click

from i2c.plan.plan_cli import register as register_plan_commands


@click.group()
def plan():
    """Plan file management commands."""
    pass


register_plan_commands(plan)
