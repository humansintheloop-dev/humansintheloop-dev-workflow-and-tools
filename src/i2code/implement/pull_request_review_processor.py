"""PullRequestReviewProcessor: processes PR review feedback."""

from i2code.implement.implement import process_pr_feedback


class PullRequestReviewProcessor:
    """Processes PR review feedback for a worktree-based workflow.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/PR/CI operations.
        state: WorkflowState (or FakeWorkflowState) for tracking processed feedback.
    """

    def __init__(self, opts, git_repo, state):
        self._opts = opts
        self._git_repo = git_repo
        self._state = state

    def process_feedback(self):
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
