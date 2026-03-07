"""TrunkMode: execute plan tasks locally on the current branch."""

import sys

from i2code.implement.claude_permissions import calculate_claude_permissions
from i2code.implement.claude_runner import print_task_failure_diagnostics
from i2code.implement.command_builder import TaskCommandOpts


class TrunkMode:
    """Execution mode that runs tasks on the current branch (no worktree/PR/CI)."""

    def __init__(self, opts, workspace, claude_services, commit_recovery):
        self._opts = opts
        self._workspace = workspace
        self._claude_services = claude_services
        self._commit_recovery = commit_recovery

    def execute(self):
        """Run the task loop until all tasks are complete."""
        self._commit_recovery.commit_if_needed()

        while True:
            next_task = self._workspace.project.get_next_task()
            if next_task is None:
                print("All tasks completed!")
                return

            self._execute_task(next_task)

    def _execute_task(self, task):
        max_attempts = 3
        task_description = task.print()

        for attempt in range(1, max_attempts + 1):
            print(f"Executing task (attempt {attempt}/{max_attempts}): {task_description}")

            result = self._claude_services.run_task(
                self._workspace.project.directory,
                task_description,
                self._task_opts(),
                self._workspace.git_repo,
            )

            if not result.succeeded:
                continue

            if self._opts.non_interactive and "<SUCCESS>" not in result.claude_result.output.stdout:
                print_task_failure_diagnostics(result.claude_result, result.head_before, result.head_after)
                sys.exit(1)

            if not self._workspace.project.is_task_completed(task.number.thread, task.number.task):
                print("Error: Task was not marked complete in plan file.", file=sys.stderr)
                continue

            return

        print(f"Error: Task failed after {max_attempts} attempts.", file=sys.stderr)
        sys.exit(1)

    def _task_opts(self):
        extra_cli_args = None
        if not self._opts.mock_claude and self._opts.non_interactive:
            permissions = calculate_claude_permissions(self._workspace.git_repo.working_tree_dir)
            extra_cli_args = ["--allowedTools", ",".join(permissions)]
        return TaskCommandOpts(
            interactive=not self._opts.non_interactive,
            extra_prompt=self._opts.extra_prompt,
            extra_cli_args=extra_cli_args,
            mock_claude=self._opts.mock_claude,
        )

