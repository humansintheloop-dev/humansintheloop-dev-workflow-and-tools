"""WorktreeMode: execute plan tasks using worktree + PR + CI loop."""

import sys

from i2code.implement.git_setup import (
    get_next_task,
    is_task_completed,
    has_ci_workflow_files,
)
from i2code.implement.implement import (
    check_claude_success,
    print_task_failure_diagnostics,
    process_pr_feedback,
)
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.pr_helpers import get_failing_workflow_run


class WorktreeMode:
    """Execution mode that runs tasks with worktree, PR creation, and CI integration.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/PR/CI operations.
        project: IdeaProject with directory, name, and plan_file.
        state: WorkflowState (or FakeWorkflowState) for tracking processed feedback.
        claude_runner: ClaudeRunner (or FakeClaudeRunner) for invoking Claude.
        work_plan_file: Path to the plan file in the working directory.
        ci_monitor: GithubActionsMonitor for waiting on CI completion.
    """

    def __init__(self, opts, git_repo, project, state, claude_runner,
                 work_plan_file, ci_monitor):
        self._opts = opts
        self._git_repo = git_repo
        self._project = project
        self._state = state
        self._claude_runner = claude_runner
        self._work_plan_file = work_plan_file
        self._ci_monitor = ci_monitor

    def execute(self):
        """Run the worktree task loop until all tasks are complete."""
        while True:
            if self._check_and_fix_ci():
                continue

            if self._process_feedback():
                continue

            next_task = get_next_task(self._work_plan_file)
            if next_task is None:
                self._print_completion()
                return

            self._execute_task(next_task)

    def _check_and_fix_ci(self):
        """Check for failing CI on current HEAD and attempt to fix it.

        Returns True if a CI failure was found (caller should loop back).
        """
        if not self._git_repo.branch_has_been_pushed():
            return False

        failing_run = get_failing_workflow_run(
            self._git_repo.branch, self._git_repo.head_sha,
            gh_client=self._git_repo.gh_client,
        )

        if not failing_run:
            return False

        workflow_name = failing_run.get("name", "unknown")
        print(f"CI build failing for HEAD ({self._git_repo.head_sha[:8]}): {workflow_name}")
        print("Attempting to fix CI failure...")

        if not self._git_repo.fix_ci_failure(
            worktree_path=self._git_repo.working_tree_dir,
            max_retries=self._opts.ci_fix_retries,
            interactive=not self._opts.non_interactive,
            mock_claude=self._opts.mock_claude,
        ):
            print("Error: Could not fix CI failure after max retries", file=sys.stderr)
            sys.exit(1)

        return True

    def _process_feedback(self):
        """Process PR feedback if any exists.

        Returns True if feedback was found (caller should loop back).
        """
        if not self._git_repo.pr_number or not self._git_repo.branch_has_been_pushed():
            return False

        pr_url = self._git_repo.gh_client.get_pr_url(self._git_repo.pr_number)
        had_feedback, _made_changes = process_pr_feedback(
            pr_number=self._git_repo.pr_number,
            pr_url=pr_url,
            state=self._state,
            worktree_path=self._git_repo.working_tree_dir,
            slice_branch=self._git_repo.branch,
            interactive=not self._opts.non_interactive,
            mock_claude=self._opts.mock_claude,
            skip_ci_wait=self._opts.skip_ci_wait,
            ci_timeout=self._opts.ci_timeout,
            gh_client=self._git_repo.gh_client,
        )

        if had_feedback:
            self._state.save()
            return True

        return False

    def _execute_task(self, next_task):
        """Execute a single task: run Claude, push, create PR, wait for CI."""
        task_description = next_task.print()
        print(f"Executing task: {task_description}")

        self._run_claude_and_validate(next_task, task_description)
        self._push_and_ensure_pr()
        self._wait_for_ci()

    def _run_claude_and_validate(self, next_task, task_description):
        """Run Claude on the task and validate the result."""
        head_before = self._git_repo.head_sha

        claude_cmd = self._build_command(task_description)
        claude_result = self._run_claude(claude_cmd)

        head_after = self._git_repo.head_sha

        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            sys.exit(1)

        if self._opts.non_interactive:
            if "<SUCCESS>" not in claude_result.stdout:
                print_task_failure_diagnostics(claude_result, head_before, head_after)
                sys.exit(1)

        if not is_task_completed(self._work_plan_file, next_task.number.thread, next_task.number.task):
            print("Error: Task was not marked complete in plan file.", file=sys.stderr)
            sys.exit(1)

        if not has_ci_workflow_files(self._git_repo.working_tree_dir):
            print("Error: No GitHub Actions workflow file found in .github/workflows/", file=sys.stderr)
            print("Tasks must create a CI workflow (e.g., .github/workflows/ci.yml) before pushing.", file=sys.stderr)
            sys.exit(1)

    def _push_and_ensure_pr(self):
        """Push changes and create a Draft PR if one doesn't exist."""
        print("Task completed successfully. Pushing changes...")

        if not self._git_repo.push():
            print("Error: Could not push commit to slice branch", file=sys.stderr)
            sys.exit(1)

        if self._git_repo.pr_number is None:
            self._git_repo.ensure_pr(
                self._project.directory, self._project.name,
                self._state.slice_number,
            )
            print(f"Created Draft PR #{self._git_repo.pr_number}")

    def _wait_for_ci(self):
        """Wait for CI completion if configured."""
        self._ci_monitor.wait_for_ci()

    def _print_completion(self):
        """Print completion message with PR URL if available."""
        print("All tasks completed!")
        if self._git_repo.pr_number:
            pr_url = self._git_repo.gh_client.get_pr_url(self._git_repo.pr_number)
            if pr_url:
                print(f"PR: {pr_url}")

    def _build_command(self, task_description):
        if self._opts.mock_claude:
            return [self._opts.mock_claude, task_description]

        return CommandBuilder().build_task_command(
            self._project.directory,
            task_description,
            interactive=not self._opts.non_interactive,
            extra_prompt=self._opts.extra_prompt,
        )

    def _run_claude(self, claude_cmd):
        work_dir = self._git_repo.working_tree_dir
        if self._opts.non_interactive:
            return self._claude_runner.run_with_capture(claude_cmd, cwd=work_dir)
        else:
            return self._claude_runner.run_interactive(claude_cmd, cwd=work_dir)
