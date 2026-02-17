"""GitRepository: wraps GitPython Repo for branch, worktree, and HEAD operations.

Provides an injectable interface for Git operations, enabling
FakeGitRepository in tests without unittest.mock.patch.
"""

import os
import shutil
import subprocess
import sys

from i2code.implement.implement import (
    generate_pr_title,
    generate_pr_body,
    get_failing_workflow_run,
    build_ci_fix_command,
    run_claude_with_output_capture,
    run_claude_interactive,
)


class GitRepository:
    """Wraps a GitPython Repo with high-level branch and worktree operations.

    Args:
        repo: A GitPython Repo instance.
        gh_client: Optional GitHubClient for PR and CI operations.
    """

    def __init__(self, repo, gh_client=None):
        self._repo = repo
        self._gh_client = gh_client
        self._branch = None
        self._pr_number = None

    @property
    def branch(self):
        return self._branch

    @branch.setter
    def branch(self, value):
        self._branch = value

    @property
    def pr_number(self):
        return self._pr_number

    @pr_number.setter
    def pr_number(self, value):
        self._pr_number = value

    @property
    def working_tree_dir(self):
        return self._repo.working_tree_dir

    @property
    def head_sha(self):
        return self._repo.head.commit.hexsha

    def head_advanced_since(self, original_sha):
        """Return True if HEAD has moved past the given SHA."""
        return self._repo.head.commit.hexsha != original_sha

    def ensure_branch(self, branch_name, from_ref=None, remote=False):
        """Ensure a branch exists, creating it if necessary.

        Args:
            branch_name: Name of the branch to ensure.
            from_ref: Optional branch name to create from. Defaults to HEAD.
            remote: When True, try tracking remote branch before falling back to HEAD.

        Returns:
            The branch name.
        """
        existing = [b.name for b in self._repo.branches]
        if branch_name not in existing:
            if remote:
                try:
                    remote_ref = self._repo.remotes.origin.refs[branch_name]
                    self._repo.create_head(branch_name, remote_ref)
                except (IndexError, AttributeError):
                    self._repo.create_head(branch_name)
            elif from_ref:
                ref = self._repo.heads[from_ref]
                self._repo.create_head(branch_name, ref)
            else:
                self._repo.create_head(branch_name)
        return branch_name

    def checkout(self, branch_name):
        """Check out the named branch."""
        self._repo.git.checkout(branch_name)

    def ensure_worktree(self, idea_name, branch_name):
        """Ensure a worktree exists for the given idea and branch.

        Args:
            idea_name: Name of the idea (used in worktree directory naming).
            branch_name: Branch to check out in the worktree.

        Returns:
            Absolute path to the worktree directory.
        """
        repo_root = self._repo.working_tree_dir
        repo_name = os.path.basename(repo_root)
        parent_dir = os.path.dirname(repo_root)

        worktree_path = os.path.join(parent_dir, f"{repo_name}-wt-{idea_name}")

        if not os.path.isdir(worktree_path):
            self._repo.git.worktree("add", worktree_path, branch_name)

        # Copy .claude/settings.local.json if it exists
        source_settings = os.path.join(repo_root, ".claude", "settings.local.json")
        if os.path.isfile(source_settings):
            dest_claude_dir = os.path.join(worktree_path, ".claude")
            os.makedirs(dest_claude_dir, exist_ok=True)
            dest_settings = os.path.join(dest_claude_dir, "settings.local.json")
            shutil.copy2(source_settings, dest_settings)

        return worktree_path

    def branch_has_been_pushed(self):
        """Check if the tracked branch exists on the remote.

        Returns:
            True if the branch exists on origin, False otherwise.
        """
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", self._branch],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and self._branch in result.stdout

    def push(self):
        """Push the tracked branch to origin.

        Returns:
            True if push succeeded, False otherwise.
        """
        result = subprocess.run(
            ["git", "push", "-u", "origin", self._branch],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Error pushing branch: {result.stderr}", file=sys.stderr)
            return False
        return True

    def ensure_pr(self, idea_directory, idea_name, slice_number, base_branch):
        """Ensure a Draft PR exists for the tracked branch.

        Creates a new Draft PR if none exists, otherwise returns the existing
        PR number. Updates self.pr_number with the result.

        Returns:
            The PR number.
        """
        if self._pr_number is not None:
            return self._pr_number

        existing = self._gh_client.find_pr(self._branch)
        if existing is not None:
            self._pr_number = existing
            return existing

        slice_suffix = self._branch.split("/")[-1]
        title = generate_pr_title(idea_name, slice_suffix)
        body = generate_pr_body(idea_directory, idea_name, slice_number)
        pr_number = self._gh_client.create_draft_pr(
            self._branch, title, body, base_branch
        )
        self._pr_number = pr_number
        return pr_number

    def wait_for_ci(self, timeout_seconds=600):
        """Wait for CI completion on the tracked branch and current HEAD.

        Returns:
            Tuple of (success, failing_run).
        """
        return self._gh_client.wait_for_workflow_completion(
            self._branch, self.head_sha, timeout_seconds=timeout_seconds
        )

    def fix_ci_failure(
        self,
        worktree_path,
        max_retries=3,
        interactive=True,
        mock_claude=None,
    ):
        """Attempt to fix CI failure using tracked branch and HEAD.

        Returns:
            True if CI passes, False if max retries exceeded.
        """
        current_sha = self.head_sha

        for attempt in range(1, max_retries + 1):
            print(f"\nCI fix attempt {attempt}/{max_retries}")

            failing_run = get_failing_workflow_run(
                self._branch, current_sha, gh_client=self._gh_client
            )
            if not failing_run:
                print("No failing workflow found - CI may have passed")
                return True

            run_id = failing_run.get("databaseId")
            workflow_name = failing_run.get("name", "unknown")
            print(f"  Workflow '{workflow_name}' failed (run {run_id})")

            print("  Fetching failure logs...")
            failure_logs = self._gh_client.get_workflow_failure_logs(run_id)

            if mock_claude:
                claude_cmd = [mock_claude, f"fix-ci-{run_id}"]
            else:
                claude_cmd = build_ci_fix_command(
                    run_id, workflow_name, failure_logs, interactive=interactive
                )

            print("  Invoking Claude to fix CI failure...")
            head_before = self.head_sha

            if interactive:
                run_claude_interactive(claude_cmd, cwd=worktree_path)
            else:
                run_claude_with_output_capture(claude_cmd, cwd=worktree_path)

            head_after = self.head_sha

            if head_before == head_after:
                print("  Claude did not make any commits")
                if attempt == max_retries:
                    return False
                continue

            print("  Pushing fix...")
            if not self.push():
                print("  Error: Could not push fix", file=sys.stderr)
                return False

            current_sha = head_after

            print("  Waiting for CI to complete...")
            ci_success, new_failing_run = self._gh_client.wait_for_workflow_completion(
                self._branch, current_sha
            )

            if ci_success:
                print("  CI passed!")
                return True

            if new_failing_run:
                print(f"  CI still failing: {new_failing_run.get('name', 'unknown')}")

        print(f"Max retries ({max_retries}) exceeded")
        return False
