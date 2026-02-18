"""TrunkMode: execute plan tasks locally on the current branch."""

import sys

from i2code.implement.implement import (
    get_next_task,
    is_task_completed,
    check_claude_success,
    print_task_failure_diagnostics,
    calculate_claude_permissions,
)


class TrunkMode:
    """Execution mode that runs tasks on the current branch (no worktree/PR/CI).

    Args:
        git_repo: GitRepository (or FakeGitRepository) for HEAD tracking.
        project: IdeaProject with directory, name, and plan_file.
        claude_runner: ClaudeRunner (or FakeClaudeRunner) for invoking Claude.
    """

    def __init__(self, git_repo, project, claude_runner):
        self._git_repo = git_repo
        self._project = project
        self._claude_runner = claude_runner

    def execute(
        self,
        non_interactive=False,
        mock_claude=None,
        extra_prompt=None,
    ):
        """Run the task loop until all tasks are complete."""
        while True:
            next_task = get_next_task(self._project.plan_file)
            if next_task is None:
                print("All tasks completed!")
                return

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

            if not is_task_completed(self._project.plan_file, next_task.number.thread, next_task.number.task):
                print("Error: Task was not marked complete in plan file.", file=sys.stderr)
                sys.exit(1)

    def _build_command(self, task_description, non_interactive, mock_claude, extra_prompt):
        if mock_claude:
            return [mock_claude, task_description]

        from i2code.implement.command_builder import CommandBuilder
        extra_cli_args = None
        if non_interactive:
            permissions = calculate_claude_permissions(self._git_repo.working_tree_dir)
            extra_cli_args = ["--allowedTools", ",".join(permissions)]
        return CommandBuilder().build_task_command(
            self._project.directory,
            task_description,
            interactive=not non_interactive,
            extra_prompt=extra_prompt,
            extra_cli_args=extra_cli_args,
        )

    def _run_claude(self, claude_cmd, non_interactive):
        if non_interactive:
            return self._claude_runner.run_with_capture(claude_cmd, cwd=self._git_repo.working_tree_dir)
        else:
            return self._claude_runner.run_interactive(claude_cmd, cwd=self._git_repo.working_tree_dir)
