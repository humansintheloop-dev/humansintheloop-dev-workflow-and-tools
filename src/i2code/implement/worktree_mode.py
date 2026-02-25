"""WorktreeMode: execute plan tasks using worktree + PR + CI loop."""

import sys
import time
from dataclasses import dataclass

from i2code.implement.git_setup import (
    has_ci_workflow_files,
)
from i2code.implement.claude_runner import (
    check_claude_success,
    print_task_failure_diagnostics,
)
from i2code.implement.command_builder import CommandBuilder


def _format_duration(seconds):
    rounded = int(seconds)
    if rounded < 60:
        unit = "second" if rounded == 1 else "seconds"
        return f"{rounded} {unit}"
    minutes = rounded // 60
    unit = "minute" if minutes == 1 else "minutes"
    return f"{minutes} {unit}"


@dataclass
class LoopSteps:
    """Pipeline collaborators used during the worktree task loop."""
    claude_runner: object
    state: object
    ci_monitor: object
    build_fixer: object
    review_processor: object
    commit_recovery: object
    clock: object = None


class WorktreeMode:
    """Execution mode that runs tasks with worktree, PR creation, and CI integration.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/PR/CI operations.
        work_project: IdeaProject for the working directory (may differ from project in worktree mode).
        loop_steps: LoopSteps grouping claude_runner, state, ci_monitor, build_fixer, review_processor, and commit_recovery.
    """

    def __init__(self, opts, git_repo, work_project, loop_steps):
        self._opts = opts
        self._git_repo = git_repo
        self._work_project = work_project
        self._loop_steps = loop_steps
        self._clock = loop_steps.clock or time.monotonic

    def execute(self):
        """Run the worktree task loop until all tasks are complete."""
        self._loop_steps.commit_recovery.commit_if_needed()

        if self._git_repo.branch_has_been_pushed() and self._git_repo.has_unpushed_commits():
            self._push_and_ensure_pr()

        while True:
            if self._loop_steps.build_fixer.check_and_fix_ci():
                continue

            if self._loop_steps.review_processor.process_feedback():
                continue

            next_task = self._work_project.get_next_task()
            if next_task is None:
                self._print_completion()
                return

            self._execute_task(next_task)

    def _execute_task(self, next_task):
        """Execute a single task: run Claude, push, create PR, wait for CI."""
        task_description = next_task.print()
        print(f"Executing task: {task_description}")

        start = self._clock()
        self._run_claude_and_validate(next_task, task_description)
        elapsed = self._clock() - start
        duration = _format_duration(elapsed)
        print(f"Task completed successfully in {duration}.")
        self._push_and_ensure_pr()
        self._loop_steps.ci_monitor.wait_for_ci(self._git_repo.branch, self._git_repo.head_sha)

    def _run_claude_and_validate(self, next_task, task_description):
        """Run Claude on the task and validate the result."""
        head_before = self._git_repo.head_sha

        claude_cmd = self._build_command(task_description)
        claude_result = self._run_claude(claude_cmd)

        head_after = self._git_repo.head_sha

        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            sys.exit(1)

        if self._opts.non_interactive and "<SUCCESS>" not in claude_result.output.stdout:
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            sys.exit(1)

        if not self._work_project.is_task_completed(next_task.number.thread, next_task.number.task):
            print("Error: Task was not marked complete in plan file.", file=sys.stderr)
            sys.exit(1)

        if not has_ci_workflow_files(self._git_repo.working_tree_dir):
            print("Error: No GitHub Actions workflow file found in .github/workflows/", file=sys.stderr)
            print("Tasks must create a CI workflow (e.g., .github/workflows/ci.yml) before pushing.", file=sys.stderr)
            sys.exit(1)

    def _push_and_ensure_pr(self):
        """Push changes and create a Draft PR if one doesn't exist."""
        print("Pushing changes...")

        if not self._git_repo.push():
            print("Error: Could not push commit to branch", file=sys.stderr)
            sys.exit(1)

        if self._git_repo.pr_number is None:
            self._git_repo.ensure_pr(
                self._work_project.directory, self._work_project.name,
            )
            print(f"Created Draft PR #{self._git_repo.pr_number}")

    def _print_completion(self):
        """Print completion message with PR URL if available."""
        print("All tasks completed!")
        if self._git_repo.pr_number:
            self._git_repo.gh_client.mark_pr_ready(self._git_repo.pr_number)
            print("PR marked ready for review")
            pr_url = self._git_repo.gh_client.get_pr_url(self._git_repo.pr_number)
            if pr_url:
                print(f"PR: {pr_url}")

    def _build_command(self, task_description):
        if self._opts.mock_claude:
            return [self._opts.mock_claude, task_description]

        return CommandBuilder().build_task_command(
            self._work_project.directory,
            task_description,
            interactive=not self._opts.non_interactive,
            extra_prompt=self._opts.extra_prompt,
        )

    def _run_claude(self, claude_cmd):
        return self._loop_steps.claude_runner.run(claude_cmd, cwd=self._git_repo.working_tree_dir)
