"""GitRepository: wraps GitPython Repo for branch, worktree, and HEAD operations.

Provides an injectable interface for Git operations, enabling
FakeGitRepository in tests without unittest.mock.patch.
"""

import os
import subprocess
import sys

from git import Repo

from i2code.implement.git_setup import sanitize_branch_name
from i2code.implement.pr_helpers import generate_pr_body, generate_pr_title


class GitRepository:
    """Wraps a GitPython Repo with high-level branch and worktree operations.

    Args:
        repo: A GitPython Repo instance.
        gh_client: GitHubClient for PR and CI operations.
    """

    def __init__(self, repo, gh_client):
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
    def gh_client(self):
        return self._gh_client

    @property
    def working_tree_dir(self):
        return self._repo.working_tree_dir

    @property
    def head_sha(self):
        return self._repo.head.commit.hexsha

    def set_user_config(self, name, email):
        """Set git user.name and user.email in the repo config."""
        self._repo.config_writer().set_value("user", "email", email).release()
        self._repo.config_writer().set_value("user", "name", name).release()

    def head_advanced_since(self, original_sha):
        """Return True if HEAD has moved past the given SHA."""
        return self._repo.head.commit.hexsha != original_sha

    @staticmethod
    def sanitize_branch_name(name: str) -> str:
        """Sanitize a string for use in a Git branch name."""
        return sanitize_branch_name(name)

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

    def ensure_idea_branch(self, idea_name):
        """Ensure the idea branch exists, creating from HEAD if necessary.

        Args:
            idea_name: Name of the idea.

        Returns:
            The idea branch name.
        """
        branch_name = f"idea/{idea_name}"
        return self.ensure_branch(branch_name)

    def ensure_integration_branch(self, idea_name, isolated=False):
        """Ensure the integration branch exists for the given idea.

        Args:
            idea_name: Name of the idea.
            isolated: When True, try tracking remote branch first.

        Returns:
            The integration branch name.
        """
        branch_name = f"idea/{idea_name}/integration"
        return self.ensure_branch(branch_name, remote=isolated)

    def ensure_slice_branch(self, idea_name, slice_number, slice_name, integration_branch):
        """Ensure the slice branch exists for the given idea.

        Args:
            idea_name: Name of the idea.
            slice_number: Slice number for branch naming.
            slice_name: Human-readable slice name (will be sanitized).
            integration_branch: Branch to create from.

        Returns:
            The slice branch name.
        """
        sanitized_name = self.sanitize_branch_name(slice_name)
        branch_name = f"idea/{idea_name}/{slice_number:02d}-{sanitized_name}"
        return self.ensure_branch(branch_name, from_ref=integration_branch)

    def checkout(self, branch_name):
        """Check out the named branch."""
        self._repo.git.checkout(branch_name)

    def ensure_worktree(self, idea_name, branch_name):
        """Ensure a worktree exists for the given idea and branch.

        Args:
            idea_name: Name of the idea (used in worktree directory naming).
            branch_name: Branch to check out in the worktree.

        Returns:
            A new GitRepository wrapping the worktree's Repo.
        """
        repo_root = self._repo.working_tree_dir
        repo_name = os.path.basename(repo_root)
        parent_dir = os.path.dirname(repo_root)

        worktree_path = os.path.join(parent_dir, f"{repo_name}-wt-{idea_name}")

        if not os.path.isdir(worktree_path):
            self._repo.git.worktree("add", worktree_path, branch_name)

        return GitRepository(Repo(worktree_path), gh_client=self._gh_client)

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

    def diff_file_against_head(self, file_path):
        """Return the diff of a file against HEAD.

        Returns:
            The diff output as a string, or empty string if no diff.
        """
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", file_path],
            capture_output=True,
            text=True,
            cwd=self._repo.working_tree_dir,
        )
        return result.stdout

    def show_file_at_head(self, file_path):
        """Return the content of a file at HEAD.

        Returns:
            The file content as a string.
        """
        rel_path = os.path.relpath(file_path, self._repo.working_tree_dir)
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel_path}"],
            capture_output=True,
            text=True,
            cwd=self._repo.working_tree_dir,
        )
        return result.stdout

    def ensure_pr(self, idea_directory, idea_name):
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

        base_branch = self._gh_client.get_default_branch()
        title = generate_pr_title(idea_name, idea_directory)
        body = generate_pr_body(idea_directory)
        pr_number = self._gh_client.create_draft_pr(
            self._branch, title, body, base_branch
        )
        self._pr_number = pr_number
        return pr_number

