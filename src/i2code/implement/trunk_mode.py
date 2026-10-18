"""TrunkMode: execute plan tasks locally on the current branch."""

import sys

from i2code.claude.permissions import calculate_claude_permissions
from i2code.implement.claude_runner import (
    ClaudeCodeCommand,
    check_claude_success,
    print_task_failure_diagnostics,
)
from i2code.implement.command_builder import CommandBuilder, TaskCommandOpts
from i2code.implement.console import print_message
from i2code.implement.task_selection import AllTasksSelection, ThreadSelection


class TrunkMode:
    """Execution mode that runs tasks on the current branch (no worktree/PR/CI)."""

    def __init__(self, opts, workspace, claude_runner, commit_recovery):
        self._opts = opts
        self._workspace = workspace
        self._claude_runner = claude_runner
        self._commit_recovery = commit_recovery

    def execute(self):
        """Run the task loop until the selected tasks are complete."""
        selection = self._task_selection()
        selection.validate()
        if selection.is_already_complete():
            selection.report_already_complete()
            return
        self._commit_recovery.commit_if_needed()

        while (next_task := selection.next_task()) is not None:
            self._execute_task(next_task)

        selection.report_completion()

    def _task_selection(self):
        project = self._workspace.project
        if self._opts.thread is None:
            return AllTasksSelection(project)
        return ThreadSelection(project, self._opts.thread, self._opts.idea_directory)

    def _execute_task(self, task):
        max_attempts = 3
        task_description = task.print()

        claude_cmd = self._build_command(task_description)
        head_before = self._workspace.git_repo.head_sha

        for attempt in range(1, max_attempts + 1):
            print_message(f"Executing task (attempt {attempt}/{max_attempts}): {task_description}")

            claude_result = self._run_claude(claude_cmd)
            head_after = self._workspace.git_repo.head_sha

            if not check_claude_success(claude_result.returncode, head_before, head_after):
                print_task_failure_diagnostics(claude_result, head_before, head_after)
                continue

            if self._opts.non_interactive and "<SUCCESS>" not in claude_result.output.stdout:
                print_task_failure_diagnostics(claude_result, head_before, head_after)
                sys.exit(1)

            if not self._workspace.project.is_task_completed(task.number.thread, task.number.task):
                print("Error: Task was not marked complete in plan file.", file=sys.stderr)
                continue

            return

        print(f"Error: Task failed after {max_attempts} attempts.", file=sys.stderr)
        sys.exit(1)

    def _build_command(self, task_description):
        cwd = self._workspace.git_repo.working_tree_dir
        if self._opts.mock_claude:
            return ClaudeCodeCommand(
                cwd=cwd,
                mock_command=[self._opts.mock_claude, task_description],
            )

        extra_cli_args = None
        if self._opts.non_interactive:
            permissions = calculate_claude_permissions(cwd)
            extra_cli_args = ["--allowedTools", ",".join(permissions)]
        return CommandBuilder().build_task_command(
            self._workspace.project.directory,
            task_description,
            TaskCommandOpts(
                interactive=not self._opts.non_interactive,
                extra_prompt=self._opts.extra_prompt,
                extra_cli_args=extra_cli_args,
            ),
            cwd=cwd,
        )

    def _run_claude(self, claude_cmd):
        return self._claude_runner.execute(claude_cmd)
