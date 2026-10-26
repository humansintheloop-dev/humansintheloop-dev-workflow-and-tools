"""Top-level Click group for the i2code CLI."""

import glob
import os
from pathlib import Path

import click

from i2code.claude.added_dirs import use_added_dirs
from i2code.claude.erm import use_erm_root
from i2code.completion import completion
from i2code.design_cmd.cli import design
from i2code.go_cmd.cli import go_cmd
from i2code.idea_cmd.cli import idea
from i2code.implement.cli import implement_cmd, scaffold_cmd
from i2code.improve.cli import improve
from i2code.plan.cli import plan
from i2code.setup_cmd.cli import setup_group
from i2code.spec_cmd.cli import spec
from i2code.tracking.cli import tracking


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
@click.option(
    "--erm", is_flag=True,
    help="Give Claude access to the nearest parent directory containing .erm",
)
@click.option(
    "--add-dir", "add_dirs", multiple=True,
    help="Run Claude with --add-dir DIRECTORY (repeatable)",
)
def main(with_sdkman, erm, add_dirs):
    """i2code - Idea to Code development workflow tools."""
    if with_sdkman:
        _init_sdkman()
    if erm:
        use_erm_root(Path.cwd())
    if add_dirs:
        use_added_dirs(add_dirs)


main.add_command(plan)
main.add_command(idea)
main.add_command(spec)
main.add_command(design)
main.add_command(implement_cmd)
main.add_command(improve)
main.add_command(scaffold_cmd)
main.add_command(setup_group)
main.add_command(tracking)
main.add_command(go_cmd)
main.add_command(completion)
