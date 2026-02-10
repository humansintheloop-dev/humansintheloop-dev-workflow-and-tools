"""Click command for the implement workflow."""

import os
import subprocess
import sys

import click

from git import Repo

from i2code.implement.implement import (
    validate_idea_directory,
    validate_idea_files,
    validate_idea_files_committed,
    init_or_load_state,
    save_state,
    ensure_integration_branch,
    ensure_worktree,
    ensure_slice_branch,
    get_first_task_name,
    get_worktree_idea_directory,
    find_existing_pr,
    ensure_draft_pr,
    push_branch_to_remote,
    branch_has_been_pushed,
    get_failing_workflow_run,
    fix_ci_failure,
    get_pr_url,
    process_pr_feedback,
    parse_tasks_from_plan,
    build_claude_command,
    run_claude_with_output_capture,
    run_claude_interactive,
    check_claude_success,
    has_ci_workflow_files,
    wait_for_workflow_completion,
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
def implement_cmd(idea_directory, cleanup, mock_claude, setup_only,
                  non_interactive, extra_prompt, skip_ci_wait,
                  ci_fix_retries, ci_timeout, isolate, isolated):
    """Implement a development plan using Git worktrees and GitHub Draft PRs."""
    # Validate idea directory exists
    idea_name = validate_idea_directory(idea_directory)

    # Validate required idea files exist
    validate_idea_files(idea_directory, idea_name)

    # Validate idea files are committed to Git
    validate_idea_files_committed(idea_directory, idea_name)

    # Delegate to isolarium VM if --isolate is set
    if isolate:
        repo = Repo(idea_directory, search_parent_directories=True)
        rel_idea_dir = os.path.relpath(idea_directory, repo.working_tree_dir)
        isolarium_args = ["isolarium", "--name", f"i2code-{idea_name}", "run"]
        if not non_interactive:
            isolarium_args.append("--interactive")
        cmd = isolarium_args + ["--", "i2code", "implement", "--isolated", rel_idea_dir]
        if cleanup:
            cmd.append("--cleanup")
        if mock_claude:
            cmd.extend(["--mock-claude", mock_claude])
        if setup_only:
            cmd.append("--setup-only")
        if non_interactive:
            cmd.append("--non-interactive")
        if extra_prompt:
            cmd.extend(["--extra-prompt", extra_prompt])
        if skip_ci_wait:
            cmd.append("--skip-ci-wait")
        if ci_fix_retries != 3:
            cmd.extend(["--ci-fix-retries", str(ci_fix_retries)])
        if ci_timeout != 600:
            cmd.extend(["--ci-timeout", str(ci_timeout)])
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    # Initialize or load state
    state = init_or_load_state(idea_directory, idea_name)

    # Get repo from idea directory
    repo = Repo(idea_directory, search_parent_directories=True)

    # Create or reuse integration branch
    integration_branch = ensure_integration_branch(repo, idea_name)
    print(f"Integration branch: {integration_branch}")

    # Read plan file to get first task name for slice naming
    original_plan_file = os.path.join(idea_directory, f"{idea_name}-plan.md")
    with open(original_plan_file, "r") as f:
        plan_content = f.read()
    first_task_name = get_first_task_name(plan_content)

    # Create or reuse slice branch
    slice_branch = ensure_slice_branch(
        repo, idea_name, state["slice_number"], first_task_name, integration_branch
    )
    print(f"Slice branch: {slice_branch}")

    if isolated:
        # Running inside isolarium VM - work directly in the repo
        work_dir = repo.working_tree_dir
        work_idea_dir = idea_directory
        work_plan_file = original_plan_file
        repo.git.checkout(slice_branch)
        work_repo = repo
    else:
        # Normal mode - use a worktree
        worktree_path = ensure_worktree(repo, idea_name, integration_branch)
        print(f"Worktree: {worktree_path}")
        work_dir = worktree_path
        work_idea_dir = get_worktree_idea_directory(
            worktree_path=worktree_path,
            main_repo_idea_dir=idea_directory,
            main_repo_root=repo.working_tree_dir
        )
        work_plan_file = os.path.join(work_idea_dir, f"{idea_name}-plan.md")
        work_repo = Repo(worktree_path)
        work_repo.git.checkout(slice_branch)

    # Skip task execution if --setup-only was provided
    # Note: PR creation is deferred until after first push (when there are commits)
    if setup_only:
        print("Setup complete. Exiting (--setup-only mode).")
        return

    # Check for existing PR (creation is deferred until after first push)
    pr_number = find_existing_pr(slice_branch)
    if pr_number:
        print(f"Reusing existing PR #{pr_number}")

    # Execute tasks one by one until all are complete
    while True:
        # Check for failing CI build on current HEAD (only if branch has been pushed)
        head_sha = work_repo.head.commit.hexsha
        if branch_has_been_pushed(slice_branch):
            failing_run = get_failing_workflow_run(slice_branch, head_sha)

            if failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI build failing for HEAD ({head_sha[:8]}): {workflow_name}")
                print("Attempting to fix CI failure...")
                if not fix_ci_failure(
                    slice_branch,
                    head_sha,
                    work_dir,
                    max_retries=ci_fix_retries,
                    interactive=not non_interactive,
                    mock_claude=mock_claude
                ):
                    print("Error: Could not fix CI failure after max retries", file=sys.stderr)
                    sys.exit(1)
                # After fixing CI, loop back to check for more failures
                continue

        # Check for PR feedback (only after CI passes and PR exists)
        if pr_number and branch_has_been_pushed(slice_branch):
            pr_url = get_pr_url(pr_number)
            had_feedback, made_changes = process_pr_feedback(
                pr_number=pr_number,
                pr_url=pr_url,
                state=state,
                worktree_path=work_dir,
                slice_branch=slice_branch,
                interactive=not non_interactive,
                mock_claude=mock_claude,
                skip_ci_wait=skip_ci_wait,
                ci_timeout=ci_timeout
            )

            if had_feedback:
                # Save state after processing feedback
                save_state(idea_directory, idea_name, state)

                # Loop back to check for more feedback or CI failures
                continue

        # Re-read plan file from the worktree to get current uncompleted tasks
        with open(work_plan_file, "r") as f:
            plan_content = f.read()

        tasks = parse_tasks_from_plan(plan_content)
        if not tasks:
            print("All tasks completed!")
            break

        tasks_before = len(tasks)
        print(f"Found {tasks_before} uncompleted task(s)")

        # Execute next uncompleted task
        current_task = tasks[0]
        print(f"Executing task: {current_task}")

        # Get HEAD before Claude invocation
        head_before = work_repo.head.commit.hexsha

        # Build and run Claude command (or mock script for testing)
        if mock_claude:
            claude_cmd = [mock_claude, current_task]
            print(f"Using mock Claude: {mock_claude}")
        else:
            claude_cmd = build_claude_command(
                work_idea_dir,
                current_task,
                interactive=not non_interactive,
                extra_prompt=extra_prompt
            )
            print(f"Invoking Claude: {' '.join(claude_cmd)}")

        # Run Claude (or mock)
        # In non-interactive mode, capture output; in interactive mode, use terminal directly
        if non_interactive:
            claude_result = run_claude_with_output_capture(claude_cmd, cwd=work_dir)
        else:
            claude_result = run_claude_interactive(claude_cmd, cwd=work_dir)

        # Get HEAD after Claude invocation
        head_after = work_repo.head.commit.hexsha

        # Re-read plan to check if task was marked complete
        with open(work_plan_file, "r") as f:
            updated_plan_content = f.read()
        tasks_after = len(parse_tasks_from_plan(updated_plan_content))

        # Verify success: exit code 0, HEAD advanced, AND task count decreased
        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print(f"\nError: Task execution failed.", file=sys.stderr)
            print(f"  Exit code: {claude_result.returncode}", file=sys.stderr)
            print(f"  HEAD before: {head_before}", file=sys.stderr)
            print(f"  HEAD after: {head_after}", file=sys.stderr)

            # Display permission denials if any
            if claude_result.permission_denials:
                print(f"\nPermission denied for {len(claude_result.permission_denials)} action(s):", file=sys.stderr)
                for denial in claude_result.permission_denials:
                    tool_name = denial.get('tool_name', 'Unknown')
                    tool_input = denial.get('tool_input', {})
                    cmd = tool_input.get('command', tool_input.get('description', 'N/A'))
                    print(f"  - {tool_name}: {cmd}", file=sys.stderr)
                print(f"\nAdd missing permissions to .claude/settings.local.json", file=sys.stderr)

            if claude_result.error_message:
                print(f"\nClaude error: {claude_result.error_message}", file=sys.stderr)

            # Display last 5 messages for debugging
            if claude_result.last_messages:
                print(f"\nLast {len(claude_result.last_messages)} messages from Claude:", file=sys.stderr)
                for msg in claude_result.last_messages:
                    msg_type = msg.get('type', 'unknown')
                    if msg_type == 'assistant':
                        content = msg.get('message', {}).get('content', [])
                        for item in content:
                            if item.get('type') == 'text':
                                text = item.get('text', '')[:200]
                                print(f"  [{msg_type}] {text}...", file=sys.stderr)
                    elif msg_type == 'result':
                        result = msg.get('result', '')[:200]
                        print(f"  [{msg_type}] {result}...", file=sys.stderr)
                    else:
                        print(f"  [{msg_type}]", file=sys.stderr)

            sys.exit(1)

        if tasks_after >= tasks_before:
            print(f"Error: Task was not marked complete in plan file.", file=sys.stderr)
            print(f"  Tasks before: {tasks_before}", file=sys.stderr)
            print(f"  Tasks after: {tasks_after}", file=sys.stderr)
            sys.exit(1)

        # Verify CI workflow exists before pushing (required for CI checks)
        if not has_ci_workflow_files(work_dir):
            print("Error: No GitHub Actions workflow file found in .github/workflows/", file=sys.stderr)
            print("Tasks must create a CI workflow (e.g., .github/workflows/ci.yml) before pushing.", file=sys.stderr)
            sys.exit(1)

        print(f"Task completed successfully. Pushing changes...")

        # Push the commit to slice branch
        if not push_branch_to_remote(slice_branch):
            print("Error: Could not push commit to slice branch", file=sys.stderr)
            sys.exit(1)

        # Create PR after first push if it doesn't exist yet
        if pr_number is None:
            pr_number = ensure_draft_pr(
                slice_branch, idea_directory, idea_name, state["slice_number"]
            )
            print(f"Created Draft PR #{pr_number}")

        # Wait for CI to complete (unless --skip-ci-wait)
        if not skip_ci_wait:
            print("Waiting for CI to complete...")
            ci_success, failing_run = wait_for_workflow_completion(
                slice_branch, head_after, timeout_seconds=ci_timeout
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI failed: {workflow_name}. Will fix on next iteration.")
            elif ci_success:
                print("CI passed!")
