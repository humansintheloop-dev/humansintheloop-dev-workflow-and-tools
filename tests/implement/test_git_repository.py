"""Unit tests for GitRepository branch operations.

These tests use real GitPython repos in temp directories to verify
GitRepository correctly wraps GitPython Repo operations.
"""

import os
import tempfile

import pytest
from git import Repo

from i2code.implement.git_repository import GitRepository


@pytest.mark.unit
class TestHeadSha:

    def test_returns_current_head_commit_sha(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo)

        assert git_repo.head_sha == repo.head.commit.hexsha


@pytest.mark.unit
class TestHeadAdvancedSince:

    def test_returns_false_when_head_unchanged(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo)

        original = git_repo.head_sha
        assert git_repo.head_advanced_since(original) is False

    def test_returns_true_after_new_commit(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo)

        original = git_repo.head_sha

        # Make a new commit
        new_file = os.path.join(tmpdir, "new.txt")
        with open(new_file, "w") as f:
            f.write("new content")
        repo.index.add(["new.txt"])
        repo.index.commit("Second commit")

        assert git_repo.head_advanced_since(original) is True


@pytest.mark.unit
class TestEnsureBranch:

    def test_creates_branch_from_head(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo)

        result = git_repo.ensure_branch("feature/new-branch")

        assert result == "feature/new-branch"
        assert "feature/new-branch" in [b.name for b in repo.branches]

    def test_reuses_existing_branch(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        repo.create_head("feature/existing")
        git_repo = GitRepository(repo)

        result = git_repo.ensure_branch("feature/existing")

        assert result == "feature/existing"
        matching = [b for b in repo.branches if b.name == "feature/existing"]
        assert len(matching) == 1

    def test_creates_branch_from_named_ref(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        # Create integration branch with a commit ahead of master
        integration = repo.create_head("idea/test/integration")
        integration.checkout()
        extra = os.path.join(tmpdir, "extra.txt")
        with open(extra, "w") as f:
            f.write("extra")
        repo.index.add(["extra.txt"])
        repo.index.commit("Integration commit")

        git_repo = GitRepository(repo)
        result = git_repo.ensure_branch("idea/test/01-setup", from_ref="idea/test/integration")

        assert result == "idea/test/01-setup"
        # New branch should point to integration branch commit, not master
        new_branch_sha = repo.heads["idea/test/01-setup"].commit.hexsha
        integration_sha = repo.heads["idea/test/integration"].commit.hexsha
        assert new_branch_sha == integration_sha


@pytest.mark.unit
class TestCheckout:

    def test_checks_out_branch(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        repo.create_head("feature/checkout-test")
        git_repo = GitRepository(repo)

        git_repo.checkout("feature/checkout-test")

        assert repo.active_branch.name == "feature/checkout-test"


def _named_repo_with_branch(parent, branch_name):
    """Create a named repo directory with an initial commit and branch."""
    repo_path = os.path.join(parent, "my-repo")
    os.makedirs(repo_path)
    repo = Repo.init(repo_path)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    readme = os.path.join(repo_path, "README.md")
    with open(readme, "w") as f:
        f.write("# Test")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    repo.create_head(branch_name)
    return repo, parent


@pytest.mark.unit
class TestEnsureWorktree:

    def test_creates_worktree(self):
        with tempfile.TemporaryDirectory() as parent:
            repo, parent_dir = _named_repo_with_branch(parent, "feature/wt-test")
            git_repo = GitRepository(repo)
            worktree_path = git_repo.ensure_worktree("test-idea", "feature/wt-test")

            expected = os.path.join(parent_dir, "my-repo-wt-test-idea")
            assert worktree_path == expected
            assert os.path.isdir(worktree_path)

    def test_reuses_existing_worktree(self):
        with tempfile.TemporaryDirectory() as parent:
            repo, _ = _named_repo_with_branch(parent, "feature/wt-reuse")
            git_repo = GitRepository(repo)
            path1 = git_repo.ensure_worktree("reuse-idea", "feature/wt-reuse")
            path2 = git_repo.ensure_worktree("reuse-idea", "feature/wt-reuse")

            assert path1 == path2


@pytest.mark.unit
class TestWorkingTreeDir:

    def test_returns_repo_working_tree_dir(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo)

        assert git_repo.working_tree_dir == repo.working_tree_dir
