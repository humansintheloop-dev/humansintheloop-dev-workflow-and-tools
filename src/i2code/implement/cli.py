"""Click command for the implement workflow."""

import click

from git import Repo

from i2code.implement.git_repository import GitRepository
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixerFactory
from i2code.implement.github_client import GitHubClient
from i2code.implement.mode_factory import ModeFactory
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_command import ImplementCommand
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.pr_helpers import push_branch_to_remote
from i2code.implement.project_setup import ProjectInitializer


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
@click.option("--isolated", is_flag=True, hidden=True,
              help="Running inside isolarium VM (internal flag)")
@click.option("--trunk", is_flag=True,
              help="Execute tasks locally on the current branch (no worktree, PR, or CI)")
@click.option("--dry-run", is_flag=True,
              help="Print what mode would be used and exit without executing")
@click.option("--ignore-uncommitted-idea-changes", is_flag=True,
              help="Skip validation that idea files are committed")
def implement_cmd(**kwargs):
    """Implement a development plan using Git worktrees and GitHub Draft PRs."""
    opts = ImplementOpts(**kwargs)
    project = IdeaProject(opts.idea_directory)
    repo = Repo(project.directory, search_parent_directories=True)
    gh_client = GitHubClient()
    git_repo = GitRepository(repo, gh_client=gh_client)
    claude_runner = ClaudeRunner()
    build_fixer_factory = GithubActionsBuildFixerFactory(
        opts=opts,
        claude_runner=claude_runner,
    )
    project_initializer = ProjectInitializer(
        claude_runner=claude_runner,
        command_builder=CommandBuilder(),
        git_repo=git_repo,
        build_fixer=build_fixer_factory.create(git_repo),
        push_fn=push_branch_to_remote,
    )
    mode_factory = ModeFactory(
        opts=opts,
        claude_runner=claude_runner,
        build_fixer_factory=build_fixer_factory,
        project_initializer=project_initializer,
    )
    command = ImplementCommand(opts, project, git_repo, mode_factory)
    command.execute()


@click.command("scaffold")
@click.argument("idea_directory")
@click.option("--non-interactive", is_flag=True,
              help="Run Claude in non-interactive mode (uses -p flag)")
@click.option("--mock-claude", metavar="SCRIPT",
              help="Use mock script instead of Claude (for testing)")
@click.pass_context
def scaffold_cmd(ctx, idea_directory, non_interactive, mock_claude):
    """Generate project scaffolding for an idea directory."""
    project = IdeaProject(idea_directory)
    project.validate()
    project.validate_files()

    repo = Repo(project.directory, search_parent_directories=True)

    initializer = (ctx.obj or {}).get("project_initializer") or ProjectInitializer(
        claude_runner=ClaudeRunner(),
        command_builder=CommandBuilder(),
    )
    initializer.run_scaffolding(
        idea_directory,
        cwd=repo.working_tree_dir,
        interactive=not non_interactive,
        mock_claude=mock_claude,
    )
