"""CommitRecovery: detects and recovers from failed commits during task execution."""

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

    def _has_newly_completed_task(self, head_plan, working_tree_plan):
        for head_thread, wt_thread in zip(head_plan.threads, working_tree_plan.threads):
            for head_task, wt_task in zip(head_thread.tasks, wt_thread.tasks):
                if not head_task.is_completed and wt_task.is_completed:
                    return True
        return False
