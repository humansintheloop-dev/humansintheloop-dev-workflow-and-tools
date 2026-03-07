"""ClaudeServices: bundles claude_runner and command_builder."""

from dataclasses import dataclass

from i2code.implement.claude_runner import (
    ClaudeRunner, TaskExecutionResult, print_task_failure_diagnostics,
)
from i2code.implement.command_builder import CommandBuilder, TaskCommandOpts


@dataclass
class ClaudeServices:
    """A claude runner and the command builder it uses."""

    claude_runner: ClaudeRunner
    command_builder: CommandBuilder

    def run_task(
        self, idea_directory: str, task_description: str,
        opts: TaskCommandOpts, repo,
    ) -> TaskExecutionResult:
        """Build a task command and run it, capturing head SHA before and after."""
        cmd = self.command_builder.build_task_command(
            idea_directory, task_description, opts,
        )
        head_before = repo.head_sha
        claude_result = self.claude_runner.run(cmd, cwd=repo.working_tree_dir)
        head_after = repo.head_sha
        result = TaskExecutionResult(claude_result, head_before, head_after)
        if not result.succeeded:
            print_task_failure_diagnostics(claude_result, head_before, head_after)
        return result
