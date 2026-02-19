"""Top-level Click group for the i2code CLI."""

import glob
import os

import click

from i2code.design_cmd.cli import design
from i2code.idea_cmd.cli import idea
from i2code.implement.cli import implement_cmd, scaffold_cmd
from i2code.improve.cli import improve
from i2code.plan.cli import plan
from i2code.script_command import script_command
from i2code.setup_cmd.cli import setup_group
from i2code.spec_cmd.cli import spec
from i2code.tracking.cli import manage_tracking_cmd


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
main.add_command(idea)
main.add_command(spec)
main.add_command(design)
main.add_command(implement_cmd)
main.add_command(improve)
main.add_command(scaffold_cmd)
main.add_command(setup_group)
main.add_command(manage_tracking_cmd)

script_command(main, "go", "idea-to-code.sh", "Run the idea-to-code orchestrator.")
