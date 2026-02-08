"""Click handlers for plan-level commands."""

import sys

import click

from i2c.plan._helpers import atomic_write
from i2c.plan.plans import fix_numbering


@click.command("fix-numbering")
@click.argument("plan_file")
def fix_numbering_cmd(plan_file):
    """Renumber all threads and tasks sequentially."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    result = fix_numbering(plan)
    atomic_write(plan_file, result)
    click.echo(f"Fixed numbering in {plan_file}")


def register(group):
    """Register plan-level commands with the given Click group."""
    group.add_command(fix_numbering_cmd)
