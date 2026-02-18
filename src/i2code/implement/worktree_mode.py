"""WorktreeMode: execute plan tasks using worktree + PR + CI loop."""

import sys

from i2code.implement.implement import (
    get_next_task,
    is_task_completed,
    check_claude_success,
    print_task_failure_diagnostics,
    has_ci_workflow_files,
    get_failing_workflow_run,
    process_pr_feedback,
)


class WorktreeMode:
    """Execution mode that runs tasks with worktree, PR creation, and CI integration.

    Args:
        git_repo: GitRepository (or FakeGitRepository) for branch/push/PR/CI operations.
        project: IdeaProject with directory, name, and plan_file.
        state: WorkflowState (or FakeWorkflowState) for tracking processed feedback.
        claude_runner: ClaudeRunner (or FakeClaudeRunner) for invoking Claude.
        gh_client: GitHubClient (or FakeGitHubClient) for PR and CI operations.
        work_dir: Path to the working directory (worktree or repo root).
        work_plan_file: Path to the plan file in the working directory.
    """

    def __init__(self, git_repo, project, state, claude_runner, gh_client,
                 work_dir, work_plan_file):
        self._git_repo = git_repo
        self._project = project
        self._state = state
        self._claude_runner = claude_runner
        self._gh_client = gh_client
        self._work_dir = work_dir
        self._work_plan_file = work_plan_file

    def execute(
        self,
        non_interactive=False,
        mock_claude=None,
        extra_prompt=None,
        skip_ci_wait=False,
        ci_fix_retries=3,
        ci_timeout=600,
    ):
        """Run the worktree task loop until all tasks are complete."""
        while True:
            if self._check_and_fix_ci(non_interactive, mock_claude, ci_fix_retries):
                continue

            if self._process_feedback(non_interactive, mock_claude, skip_ci_wait, ci_timeout):
                continue

            next_task = get_next_task(self._work_plan_file)
            if next_task is None:
                self._print_completion()
                return

            self._execute_task(
                next_task, non_interactive, mock_claude, extra_prompt,
                skip_ci_wait, ci_fix_retries, ci_timeout,
            )

    def _check_and_fix_ci(self, non_interactive, mock_claude, ci_fix_retries):
        """Check for failing CI on current HEAD and attempt to fix it.

        Returns True if a CI failure was found (caller should loop back).
        """
        if not self._git_repo.branch_has_been_pushed():
            return False

        failing_run = get_failing_workflow_run(
            self._git_repo.branch, self._git_repo.head_sha,
            gh_client=self._gh_client,
        )

        if not failing_run:
            return False

        workflow_name = failing_run.get("name", "unknown")
        print(f"CI build failing for HEAD ({self._git_repo.head_sha[:8]}): {workflow_name}")
        print("Attempting to fix CI failure...")

        if not self._git_repo.fix_ci_failure(
            worktree_path=self._work_dir,
            max_retries=ci_fix_retries,
            interactive=not non_interactive,
            mock_claude=mock_claude,
        ):
            print("Error: Could not fix CI failure after max retries", file=sys.stderr)
            sys.exit(1)

        return True

    def _process_feedback(self, non_interactive, mock_claude, skip_ci_wait, ci_timeout):
        """Process PR feedback if any exists.

        Returns True if feedback was found (caller should loop back).
        """
        if not self._git_repo.pr_number or not self._git_repo.branch_has_been_pushed():
            return False

        pr_url = self._gh_client.get_pr_url(self._git_repo.pr_number)
        had_feedback, made_changes = process_pr_feedback(
            pr_number=self._git_repo.pr_number,
            pr_url=pr_url,
            state=self._state,
            worktree_path=self._work_dir,
            slice_branch=self._git_repo.branch,
            interactive=not non_interactive,
            mock_claude=mock_claude,
            skip_ci_wait=skip_ci_wait,
            ci_timeout=ci_timeout,
            gh_client=self._gh_client,
        )

        if had_feedback:
            self._state.save()
            return True

        return False

    def _execute_task(self, next_task, non_interactive, mock_claude, extra_prompt,
                      skip_ci_wait, ci_fix_retries, ci_timeout):
        """Execute a single task: run Claude, push, create PR, wait for CI."""
        task_description = next_task.print()
        print(f"Executing task: {task_description}")

        head_before = self._git_repo.head_sha

        claude_cmd = self._build_command(
            task_description, non_interactive, mock_claude, extra_prompt,
        )
        claude_result = self._run_claude(claude_cmd, non_interactive)

        head_after = self._git_repo.head_sha

        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            sys.exit(1)

        if non_interactive:
            if "<SUCCESS>" not in claude_result.stdout:
                print_task_failure_diagnostics(claude_result, head_before, head_after)
                sys.exit(1)

        if not is_task_completed(self._work_plan_file, next_task.number.thread, next_task.number.task):
            print("Error: Task was not marked complete in plan file.", file=sys.stderr)
            sys.exit(1)

        if not has_ci_workflow_files(self._work_dir):
            print("Error: No GitHub Actions workflow file found in .github/workflows/", file=sys.stderr)
            print("Tasks must create a CI workflow (e.g., .github/workflows/ci.yml) before pushing.", file=sys.stderr)
            sys.exit(1)

        print("Task completed successfully. Pushing changes...")

        if not self._git_repo.push():
            print("Error: Could not push commit to slice branch", file=sys.stderr)
            sys.exit(1)

        if self._git_repo.pr_number is None:
            base_branch = self._gh_client.get_default_branch()
            self._git_repo.ensure_pr(
                self._project.directory, self._project.name,
                self._state.slice_number, base_branch=base_branch,
            )
            print(f"Created Draft PR #{self._git_repo.pr_number}")

        if not skip_ci_wait:
            print("Waiting for CI to complete...")
            ci_success, failing_run = self._git_repo.wait_for_ci(
                timeout_seconds=ci_timeout,
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"CI failed: {workflow_name}. Will fix on next iteration.")
            elif ci_success:
                print("CI passed!")

    def _print_completion(self):
        """Print completion message with PR URL if available."""
        print("All tasks completed!")
        if self._git_repo.pr_number:
            pr_url = self._gh_client.get_pr_url(self._git_repo.pr_number)
            if pr_url:
                print(f"PR: {pr_url}")

    def _build_command(self, task_description, non_interactive, mock_claude, extra_prompt):
        if mock_claude:
            return [mock_claude, task_description]

        from i2code.implement.command_builder import CommandBuilder
        return CommandBuilder().build_task_command(
            self._project.directory,
            task_description,
            interactive=not non_interactive,
            extra_prompt=extra_prompt,
        )

    def _run_claude(self, claude_cmd, non_interactive):
        if non_interactive:
            return self._claude_runner.run_with_capture(claude_cmd, cwd=self._work_dir)
        else:
            return self._claude_runner.run_interactive(claude_cmd, cwd=self._work_dir)
