"""CommitRecovery: detects and recovers from failed commits during task execution."""

from i2code.implement.claude_runner import check_claude_success
from i2code.implement.command_builder import CommandBuilder
from i2code.plan_domain.parser import parse


class CommitRecovery:
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

    def needs_recovery(self):
        plan_file = self._project.plan_file
        diff = self._git_repo.diff_file_against_head(plan_file)
        if not diff:
            return False

        with open(plan_file, "r", encoding="utf-8") as f:
            working_tree_plan = parse(f.read())

        head_content = self._git_repo.show_file_at_head(plan_file)
        head_plan = parse(head_content)

        return self._has_newly_completed_task(head_plan, working_tree_plan)

    def recover(self):
        """Attempt to commit recovered changes via Claude.

        Returns:
            True if recovery succeeded (HEAD advanced), False otherwise.
        """
        print("Detected uncommitted changes from a previous run, attempting to commit...")

        diff_summary = self._git_repo.diff_file_against_head(self._project.plan_file)
        cmd = CommandBuilder().build_recovery_command(
            plan_file=self._project.plan_file,
            diff_summary=diff_summary,
            interactive=True,
        )

        head_before = self._git_repo.head_sha
        claude_result = self._claude_runner.run_interactive(
            cmd, cwd=self._git_repo.working_tree_dir,
        )
        head_after = self._git_repo.head_sha

        return check_claude_success(claude_result.returncode, head_before, head_after)

    def check_and_recover(self):
        """Check if recovery is needed and attempt it.

        Returns:
            True if recovery was needed and succeeded, False otherwise.
        """
        if self.needs_recovery():
            return self.recover()
        return False

    def _has_newly_completed_task(self, head_plan, working_tree_plan):
        for head_thread, wt_thread in zip(head_plan.threads, working_tree_plan.threads):
            for head_task, wt_task in zip(head_thread.tasks, wt_thread.tasks):
                if not head_task.is_completed and wt_task.is_completed:
                    return True
        return False
