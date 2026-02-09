"""Top-level Click group for the i2code CLI."""

import click

from i2code.plan.cli import plan


@click.group()
def main():
    """i2code - Idea to Code development workflow tools."""
    pass


main.add_command(plan)
