"""TaskCommitRecovery: detects and recovers from failed commits during task execution."""

import sys

from i2code.implement.claude_runner import check_claude_success, print_task_failure_diagnostics
from i2code.implement.command_builder import CommandBuilder
from i2code.plan_domain.parser import parse


class TaskCommitRecovery:
    """Detects uncommitted plan-file changes showing a fully completed task.

    Args:
        git_repo: GitRepository (or FakeGitRepository) for diff/show operations.
        project: IdeaProject with plan_file path.
        claude_runner: ClaudeRunner for re-running commit attempts.
    """

    def __init__(self, git_repo, project, claude_runner):
        self._git_repo = git_repo
        self._project = project
        self._claude_runner = claude_runner

    def has_uncommitted_completed_task(self):
        plan_file = self._project.plan_file
        diff = self._git_repo.diff_file_against_head(plan_file)
        if not diff:
            return False

        with open(plan_file, "r", encoding="utf-8") as f:
            working_tree_plan = parse(f.read())

        head_content = self._git_repo.show_file_at_head(plan_file)
        head_plan = parse(head_content)

        return self._has_newly_completed_task(head_plan, working_tree_plan)

    def commit_uncommitted_changes(self):
        """Attempt to commit recovered changes via Claude (non-interactive).

        Returns:
            True if recovery succeeded (HEAD advanced and <SUCCESS> tag present),
            False otherwise.
        """
        print("Detected uncommitted changes from a previous run, attempting to commit...")

        diff_summary = self._git_repo.diff_file_against_head(self._project.plan_file)
        cmd = CommandBuilder().build_recovery_command(
            plan_file=self._project.plan_file,
            diff_summary=diff_summary,
            interactive=False,
        )

        head_before = self._git_repo.head_sha
        claude_result = self._claude_runner.run_batch(
            cmd, cwd=self._git_repo.working_tree_dir,
        )
        head_after = self._git_repo.head_sha

        if not check_claude_success(claude_result.returncode, head_before, head_after):
            print_task_failure_diagnostics(claude_result, head_before, head_after)
            return False
        return "<SUCCESS>" in claude_result.output.stdout

    def commit_if_needed(self):
        """Check if recovery is needed and attempt it with retry.

        Attempts recovery up to 2 times. On success, prints a success message
        and returns. On double failure, prints an error message and exits.
        """
        if not self.has_uncommitted_completed_task():
            return False

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            if self.commit_uncommitted_changes():
                print("Recovery commit successful.")
                return True
            if attempt < max_attempts:
                print(f"Recovery attempt {attempt} failed, retrying...")

        print("Error: Could not commit recovered changes after 2 attempts. Please commit manually and rerun.")
        sys.exit(1)

    def _has_newly_completed_task(self, head_plan, working_tree_plan):
        for head_thread, wt_thread in zip(head_plan.threads, working_tree_plan.threads):
            for head_task, wt_task in zip(head_thread.tasks, wt_thread.tasks):
                if not head_task.is_completed and wt_task.is_completed:
                    return True
        return False
