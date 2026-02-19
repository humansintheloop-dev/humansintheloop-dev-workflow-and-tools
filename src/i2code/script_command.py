"""Factory for creating Click commands that delegate to bundled shell scripts."""

import sys

import click

from i2code.script_runner import run_script


def script_command(group, name, script_name, help_text):
    """Register a Click command on *group* that forwards args to a bundled script."""

    @group.command(name, context_settings={"ignore_unknown_options": True})
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def cmd(args):
        result = run_script(script_name, args)
        sys.exit(result.returncode)

    cmd.help = help_text
