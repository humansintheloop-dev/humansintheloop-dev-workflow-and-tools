"""Click command for the implement workflow."""

import click

from i2code.implement.command_assembler import (
    assemble_command,
    assemble_implement,
    assemble_scaffold,
)
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.scaffold_opts import ScaffoldOpts


@click.command("implement")
@click.argument("idea_directory")
@click.option("--cleanup", is_flag=True,
              help="Perform cleanup (remove worktree, delete local branches) after PR is merged/closed")
@click.option("--mock-claude", metavar="SCRIPT",
              help="Use mock script instead of Claude (for testing)")
@click.option("--setup-only", is_flag=True,
              help="Only set up infrastructure (branches, worktree, PR), don't execute tasks")
@click.option("--non-interactive", is_flag=True,
              help="Run Claude in non-interactive mode (uses -p flag)")
@click.option("--extra-prompt", metavar="TEXT",
              help="Extra text to append to Claude's prompt (after a blank line)")
@click.option("--skip-ci-wait", is_flag=True,
              help="Skip waiting for CI after push (for testing)")
@click.option("--ci-fix-retries", type=int, default=3,
              help="Maximum retries for fixing CI failures (default: 3)")
@click.option("--ci-timeout", type=int, default=600,
              help="Timeout in seconds for CI completion (default: 600)")
@click.option("--isolate", is_flag=True,
              help="Run inside an isolarium VM")
@click.option("--isolation-type", metavar="TYPE",
              help="Isolation environment type (passed as --type to isolarium)")
@click.option("--isolated", is_flag=True, hidden=True,
              help="Running inside isolarium VM (internal flag)")
@click.option("--trunk", is_flag=True,
              help="Execute tasks locally on the current branch (no worktree, PR, or CI)")
@click.option("--dry-run", is_flag=True,
              help="Print what mode would be used and exit without executing")
@click.option("--ignore-uncommitted-idea-changes", is_flag=True,
              help="Skip validation that idea files are committed")
@click.option("--address-review-comments", is_flag=True,
              help="Keep running after tasks complete, polling for and addressing PR review comments")
@click.pass_context
def implement_cmd(ctx, **kwargs):
    """Implement a development plan using Git worktrees and GitHub Draft PRs."""
    command = assemble_command(ctx, assemble_implement, ImplementOpts(**kwargs))
    command.execute()


@click.command("scaffold")
@click.argument("idea_directory")
@click.option("--non-interactive", is_flag=True,
              help="Run Claude in non-interactive mode (uses -p flag)")
@click.option("--mock-claude", metavar="SCRIPT",
              help="Use mock script instead of Claude (for testing)")
@click.pass_context
def scaffold_cmd(ctx, **kwargs):
    """Generate project scaffolding for an idea directory."""
    command = assemble_command(ctx, assemble_scaffold, ScaffoldOpts(**kwargs))
    command.execute()
