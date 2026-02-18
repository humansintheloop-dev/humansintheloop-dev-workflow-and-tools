"""GithubActionsBuildFixer: detects and fixes CI failures on current HEAD."""

import sys

from i2code.implement.pr_helpers import get_failing_workflow_run


class GithubActionsBuildFixer:
    """Checks for failing CI on the current HEAD and attempts to fix it.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/CI operations.
    """

    def __init__(self, opts, git_repo):
        self._opts = opts
        self._git_repo = git_repo

    def check_and_fix_ci(self):
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
