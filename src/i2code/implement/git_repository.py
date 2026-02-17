"""GitRepository: wraps GitPython Repo for branch, worktree, and HEAD operations.

Provides an injectable interface for Git operations, enabling
FakeGitRepository in tests without unittest.mock.patch.
"""

import os
import shutil


class GitRepository:
    """Wraps a GitPython Repo with high-level branch and worktree operations.

    Args:
        repo: A GitPython Repo instance.
    """

    def __init__(self, repo):
        self._repo = repo

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
