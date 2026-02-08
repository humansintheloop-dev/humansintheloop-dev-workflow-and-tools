"""Top-level Click group for the i2c CLI."""

import click

from i2c.plan.cli import plan


@click.group()
def main():
    """i2c - Idea to Code development workflow tools."""
    pass


main.add_command(plan)
