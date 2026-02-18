"""Click command for the implement workflow."""

import sys

import click

from git import Repo

from i2code.implement.git_repository import GitRepository
from i2code.implement.github_client import GitHubClient
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.workflow_state import WorkflowState
from i2code.implement.git_setup import (
    validate_idea_files_committed,
    ensure_claude_permissions,
    get_next_task,
)
from i2code.implement.claude_runner import RealClaudeRunner
from i2code.implement.isolate_mode import IsolateMode, RealProjectSetup, RealSubprocessRunner
from i2code.implement.project_setup import run_scaffolding
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.worktree_mode import WorktreeMode


def implement(opts: ImplementOpts, project: IdeaProject, repo, git_repo, claude_runner, gh_client):
    """Implement a development plan using Git worktrees and GitHub Draft PRs."""
    project.validate()
    project.validate_files()

    if opts.dry_run:
        if opts.trunk:
            mode = "trunk"
        elif opts.isolate:
            mode = "isolate"
        else:
            mode = "worktree"
        print(f"Mode: {mode}")
        print(f"Idea: {project.name}")
        print(f"Directory: {project.directory}")
        return

    if not opts.isolated and not opts.ignore_uncommitted_idea_changes:
        validate_idea_files_committed(project)

    if opts.trunk:
        implement_trunk_mode(opts, project, git_repo, claude_runner, gh_client)
    elif opts.isolate:
        implement_isolate_mode(opts, project, repo, git_repo, claude_runner, gh_client)
    else:
        implement_worktree_mode(opts, project, repo, git_repo, claude_runner, gh_client)


def implement_trunk_mode(opts: ImplementOpts, project: IdeaProject, git_repo, claude_runner, gh_client):
    """Execute tasks locally on the current branch."""
    opts.validate_trunk_options()

    trunk_mode = TrunkMode(
        git_repo=git_repo,
        project=project,
        claude_runner=claude_runner,
    )
    trunk_mode.execute(
        non_interactive=opts.non_interactive,
        mock_claude=opts.mock_claude,
        extra_prompt=opts.extra_prompt,
    )


def implement_isolate_mode(opts: ImplementOpts, project: IdeaProject, repo, git_repo, claude_runner, gh_client):
    """Delegate execution to an isolarium VM."""
    isolate_mode = IsolateMode(
        repo=repo,
        git_repo=git_repo,
        project=project,
        gh_client=gh_client,
        project_setup=RealProjectSetup(),
        subprocess_runner=RealSubprocessRunner(),
    )
    returncode = isolate_mode.execute(
        non_interactive=opts.non_interactive,
        mock_claude=opts.mock_claude,
        cleanup=opts.cleanup,
        setup_only=opts.setup_only,
        extra_prompt=opts.extra_prompt,
        skip_ci_wait=opts.skip_ci_wait,
        ci_fix_retries=opts.ci_fix_retries,
        ci_timeout=opts.ci_timeout,
    )
    sys.exit(returncode)


def implement_worktree_mode(opts: ImplementOpts, project: IdeaProject, repo, git_repo, claude_runner, gh_client):
    """Execute tasks using worktree + PR + CI loop."""
    state = WorkflowState.load(project.state_file)

    integration_branch = git_repo.ensure_integration_branch(project.name, isolated=opts.isolated)
    print(f"Integration branch: {integration_branch}")

    next_task = get_next_task(project.plan_file)
    first_task_name = next_task.task.title if next_task else "implementation"

    slice_branch = git_repo.ensure_slice_branch(
        project.name, state.slice_number, first_task_name, integration_branch
    )
    print(f"Slice branch: {slice_branch}")

    if opts.isolated:
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test User").release()
        ensure_claude_permissions(git_repo.working_tree_dir)
        work_plan_file = project.plan_file
        git_repo.checkout(slice_branch)
    else:
        git_repo = git_repo.ensure_worktree(project.name, integration_branch)
        print(f"Worktree: {git_repo.working_tree_dir}")
        ensure_claude_permissions(git_repo.working_tree_dir)
        work_project = project.worktree_idea_project(git_repo.working_tree_dir, repo.working_tree_dir)
        work_plan_file = work_project.plan_file
        git_repo.checkout(slice_branch)

    git_repo.branch = slice_branch

    if opts.setup_only:
        print("Setup complete. Exiting (--setup-only mode).")
        return

    existing_pr = gh_client.find_pr(slice_branch)
    if existing_pr:
        git_repo.pr_number = existing_pr
        print(f"Reusing existing PR #{existing_pr}")

    worktree_mode = WorktreeMode(
        opts=opts,
        git_repo=git_repo,
        project=project,
        state=state,
        claude_runner=claude_runner,
        gh_client=gh_client,
        work_plan_file=work_plan_file,
    )
    worktree_mode.execute()


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
    claude_runner = RealClaudeRunner()
    implement(opts, project, repo, git_repo, claude_runner, gh_client)


@click.command("scaffold")
@click.argument("idea_directory")
@click.option("--non-interactive", is_flag=True,
              help="Run Claude in non-interactive mode (uses -p flag)")
@click.option("--mock-claude", metavar="SCRIPT",
              help="Use mock script instead of Claude (for testing)")
def scaffold_cmd(idea_directory, non_interactive, mock_claude):
    """Generate project scaffolding for an idea directory."""
    project = IdeaProject(idea_directory)
    project.validate()
    project.validate_files()

    repo = Repo(project.directory, search_parent_directories=True)

    run_scaffolding(
        idea_directory,
        cwd=repo.working_tree_dir,
        interactive=not non_interactive,
        mock_claude=mock_claude,
    )
