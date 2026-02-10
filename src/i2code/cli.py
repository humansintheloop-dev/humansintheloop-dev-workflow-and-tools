"""Top-level Click group for the i2code CLI."""

import glob
import os

import click

from i2code.implement.cli import implement_cmd
from i2code.plan.cli import plan


def _init_sdkman():
    """Add SDKMAN candidate bins to PATH."""
    sdkman_dir = os.path.expanduser("~/.sdkman/candidates")
    if not os.path.isdir(sdkman_dir):
        return
    bins = sorted(glob.glob(os.path.join(sdkman_dir, "*/current/bin")))
    if bins:
        os.environ["PATH"] = os.pathsep.join(bins) + os.pathsep + os.environ.get("PATH", "")


@click.group()
@click.option("--with-sdkman", is_flag=True, help="Add SDKMAN-installed tools to PATH")
def main(with_sdkman):
    """i2code - Idea to Code development workflow tools."""
    if with_sdkman:
        _init_sdkman()


main.add_command(plan)
main.add_command(implement_cmd)
