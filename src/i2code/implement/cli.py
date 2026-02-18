"""Click command for the implement workflow."""

import os
import subprocess
import sys

import click

from git import Repo

from i2code.implement.git_repository import GitRepository
from i2code.implement.github_client import GitHubClient
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.workflow_state import WorkflowState
from i2code.implement.implement import (
    validate_idea_files_committed,
    ensure_integration_branch,
    ensure_project_setup,
    ensure_claude_permissions,
    ensure_worktree,
    ensure_slice_branch,
    get_next_task,
    get_worktree_idea_directory,
    run_scaffolding,
)
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.worktree_mode import WorktreeMode


def implement(opts: ImplementOpts, project: IdeaProject):
    """Implement a development plan using Git worktrees and GitHub Draft PRs."""
    project.validate()
    project.validate_files()

    if not opts.isolated and not opts.ignore_uncommitted_idea_changes:
        validate_idea_files_committed(project.directory, project.name)

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

    # Trunk mode: execute tasks locally on current branch
    if opts.trunk:
        incompatible = []
        if opts.cleanup:
            incompatible.append("--cleanup")
        if opts.setup_only:
            incompatible.append("--setup-only")
        if opts.isolate:
            incompatible.append("--isolate")
        if opts.isolated:
            incompatible.append("--isolated")
        if opts.skip_ci_wait:
            incompatible.append("--skip-ci-wait")
        if opts.ci_fix_retries != 3:
            incompatible.append("--ci-fix-retries")
        if opts.ci_timeout != 600:
            incompatible.append("--ci-timeout")
        if incompatible:
            raise click.UsageError(
                f"--trunk cannot be combined with: {', '.join(incompatible)}"
            )

        from i2code.implement.claude_runner import RealClaudeRunner

        repo = Repo(project.directory, search_parent_directories=True)
        git_repo = GitRepository(repo)
        claude_runner = RealClaudeRunner()

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
        return

    # Delegate to isolarium VM if --isolate is set
    if opts.isolate:
        repo = Repo(project.directory, search_parent_directories=True)
        gh_client = GitHubClient()

        # Run project scaffolding on host before delegating to VM
        integration_branch = ensure_integration_branch(repo, project.name)
        setup_ok = ensure_project_setup(
            repo=repo,
            idea_directory=project.directory,
            idea_name=project.name,
            integration_branch=integration_branch,
            interactive=not opts.non_interactive,
            mock_claude=opts.mock_claude,
            ci_fix_retries=opts.ci_fix_retries,
            ci_timeout=opts.ci_timeout,
            skip_ci_wait=opts.skip_ci_wait,
            gh_client=gh_client,
        )
        if not setup_ok:
            print("Error: Project scaffolding setup failed", file=sys.stderr)
            sys.exit(1)

        rel_idea_dir = os.path.relpath(project.directory, repo.working_tree_dir)
        isolarium_args = ["isolarium", "--name", f"i2code-{project.name}", "run"]
        if not opts.non_interactive:
            isolarium_args.append("--interactive")
        cmd = isolarium_args + ["--", "i2code", "--with-sdkman", "implement", "--isolated", rel_idea_dir]
        if opts.cleanup:
            cmd.append("--cleanup")
        if opts.mock_claude:
            cmd.extend(["--mock-claude", opts.mock_claude])
        if opts.setup_only:
            cmd.append("--setup-only")
        if opts.non_interactive:
            cmd.append("--non-interactive")
        if opts.extra_prompt:
            cmd.extend(["--extra-prompt", opts.extra_prompt])
        if opts.skip_ci_wait:
            cmd.append("--skip-ci-wait")
        if opts.ci_fix_retries != 3:
            cmd.extend(["--ci-fix-retries", str(opts.ci_fix_retries)])
        if opts.ci_timeout != 600:
            cmd.extend(["--ci-timeout", str(opts.ci_timeout)])
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    # Initialize or load state
    state = WorkflowState.load(project.state_file)

    # Get repo from idea directory
    repo = Repo(project.directory, search_parent_directories=True)

    # Create or reuse integration branch
    integration_branch = ensure_integration_branch(repo, project.name, isolated=opts.isolated)
    print(f"Integration branch: {integration_branch}")

    # Read plan file to get first task name for slice naming
    next_task = get_next_task(project.plan_file)
    first_task_name = next_task.task.title if next_task else "implementation"

    # Create or reuse slice branch
    slice_branch = ensure_slice_branch(
        repo, project.name, state.slice_number, first_task_name, integration_branch
    )
    print(f"Slice branch: {slice_branch}")

    # Create GitHubClient for PR operations
    gh_client = GitHubClient()

    if opts.isolated:
        # Running inside isolarium VM - work directly in the repo
        work_dir = repo.working_tree_dir
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test User").release()
        ensure_claude_permissions(work_dir)
        work_idea_dir = project.directory
        work_plan_file = project.plan_file
        repo.git.checkout(slice_branch)
        git_repo = GitRepository(repo, gh_client=gh_client)
    else:
        # Normal mode - use a worktree
        worktree_path = ensure_worktree(repo, project.name, integration_branch)
        print(f"Worktree: {worktree_path}")
        work_dir = worktree_path
        ensure_claude_permissions(work_dir)
        work_idea_dir = get_worktree_idea_directory(
            worktree_path=worktree_path,
            main_repo_idea_dir=project.directory,
            main_repo_root=repo.working_tree_dir
        )
        work_plan_file = os.path.join(work_idea_dir, f"{project.name}-plan.md")
        work_repo = Repo(worktree_path)
        work_repo.git.checkout(slice_branch)
        git_repo = GitRepository(work_repo, gh_client=gh_client)

    git_repo.branch = slice_branch

    # Skip task execution if --setup-only was provided
    # Note: PR creation is deferred until after first push (when there are commits)
    if opts.setup_only:
        print("Setup complete. Exiting (--setup-only mode).")
        return

    # Check for existing PR (creation is deferred until after first push)
    existing_pr = gh_client.find_pr(slice_branch)
    if existing_pr:
        git_repo.pr_number = existing_pr
        print(f"Reusing existing PR #{existing_pr}")

    from i2code.implement.claude_runner import RealClaudeRunner

    worktree_mode = WorktreeMode(
        git_repo=git_repo,
        project=project,
        state=state,
        claude_runner=RealClaudeRunner(),
        gh_client=gh_client,
        work_dir=work_dir,
        work_plan_file=work_plan_file,
    )
    worktree_mode.execute(
        non_interactive=opts.non_interactive,
        mock_claude=opts.mock_claude,
        extra_prompt=opts.extra_prompt,
        skip_ci_wait=opts.skip_ci_wait,
        ci_fix_retries=opts.ci_fix_retries,
        ci_timeout=opts.ci_timeout,
    )


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
    implement(opts, project)


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
