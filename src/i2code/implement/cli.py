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
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.implement import (
    validate_idea_files_committed,
    ensure_integration_branch,
    ensure_project_setup,
    ensure_claude_permissions,
    ensure_worktree,
    ensure_slice_branch,
    get_next_task,
    is_task_completed,
    get_worktree_idea_directory,
    process_pr_feedback,
    run_claude_with_output_capture,
    run_claude_interactive,
    run_scaffolding,
    check_claude_success,
    has_ci_workflow_files,
    run_trunk_loop,
    print_task_failure_diagnostics,
)


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

        run_trunk_loop(
            idea_directory=project.directory,
            idea_name=project.name,
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

    # Execute tasks one by one until all are complete
    while True:
        # Check for failing CI build on current HEAD (only if branch has been pushed)
        if git_repo.branch_has_been_pushed():
            from i2code.implement.implement import get_failing_workflow_run
            head_sha = git_repo.head_sha
            failing_run = get_failing_workflow_run(
                git_repo.branch, head_sha, gh_client=gh_client
            )

            if failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI build failing for HEAD ({head_sha[:8]}): {workflow_name}")
                print("Attempting to fix CI failure...")
                if not git_repo.fix_ci_failure(
                    worktree_path=work_dir,
                    max_retries=opts.ci_fix_retries,
                    interactive=not opts.non_interactive,
                    mock_claude=opts.mock_claude,
                ):
                    print("Error: Could not fix CI failure after max retries", file=sys.stderr)
                    sys.exit(1)
                # After fixing CI, loop back to check for more failures
                continue

        # Check for PR feedback (only after CI passes and PR exists)
        if git_repo.pr_number and git_repo.branch_has_been_pushed():
            pr_url = gh_client.get_pr_url(git_repo.pr_number)
            had_feedback, made_changes = process_pr_feedback(
                pr_number=git_repo.pr_number,
                pr_url=pr_url,
                state=state,
                worktree_path=work_dir,
                slice_branch=git_repo.branch,
                interactive=not opts.non_interactive,
                mock_claude=opts.mock_claude,
                skip_ci_wait=opts.skip_ci_wait,
                ci_timeout=opts.ci_timeout,
                gh_client=gh_client,
            )

            if had_feedback:
                # Save state after processing feedback
                state.save()

                # Loop back to check for more feedback or CI failures
                continue

        # Get next uncompleted task from the plan
        next_task = get_next_task(work_plan_file)
        if next_task is None:
            print("All tasks completed!")
            if git_repo.pr_number:
                pr_url = gh_client.get_pr_url(git_repo.pr_number)
                if pr_url:
                    print(f"PR: {pr_url}")
            break

        task_description = next_task.print()
        print(f"Executing task: {task_description}")

        # Get HEAD before Claude invocation
        head_before = git_repo.head_sha

        # Build and run Claude command (or mock script for testing)
        if opts.mock_claude:
            claude_cmd = [opts.mock_claude, task_description]
            print(f"Using mock Claude: {opts.mock_claude}")
        else:
            claude_cmd = CommandBuilder().build_task_command(
                work_idea_dir,
                task_description,
                interactive=not opts.non_interactive,
                extra_prompt=opts.extra_prompt,
            )
            print(f"Invoking Claude: {' '.join(claude_cmd)}")

        # Run Claude (or mock)
        # In non-interactive mode, capture output; in interactive mode, use terminal directly
        if opts.non_interactive:
            claude_result = run_claude_with_output_capture(claude_cmd, cwd=work_dir)
        else:
            claude_result = run_claude_interactive(claude_cmd, cwd=work_dir)

        head_after = git_repo.head_sha

        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            sys.exit(1)

        # In non-interactive mode, also check for outcome tags
        if opts.non_interactive:
            if "<SUCCESS>" not in claude_result.stdout:
                print_task_failure_diagnostics(claude_result, head_before, head_after)
                sys.exit(1)

        if not is_task_completed(work_plan_file, next_task.number.thread, next_task.number.task):
            print("Error: Task was not marked complete in plan file.", file=sys.stderr)
            sys.exit(1)

        # Verify CI workflow exists before pushing (required for CI checks)
        if not has_ci_workflow_files(work_dir):
            print("Error: No GitHub Actions workflow file found in .github/workflows/", file=sys.stderr)
            print("Tasks must create a CI workflow (e.g., .github/workflows/ci.yml) before pushing.", file=sys.stderr)
            sys.exit(1)

        print("Task completed successfully. Pushing changes...")

        # Push the commit to slice branch
        if not git_repo.push():
            print("Error: Could not push commit to slice branch", file=sys.stderr)
            sys.exit(1)

        # Create PR after first push if it doesn't exist yet
        if git_repo.pr_number is None:
            base_branch = gh_client.get_default_branch()
            git_repo.ensure_pr(
                project.directory, project.name, state.slice_number,
                base_branch=base_branch,
            )
            print(f"Created Draft PR #{git_repo.pr_number}")

        # Wait for CI to complete (unless --skip-ci-wait)
        if not opts.skip_ci_wait:
            print("Waiting for CI to complete...")
            ci_success, failing_run = git_repo.wait_for_ci(
                timeout_seconds=opts.ci_timeout
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI failed: {workflow_name}. Will fix on next iteration.")
            elif ci_success:
                print("CI passed!")


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
