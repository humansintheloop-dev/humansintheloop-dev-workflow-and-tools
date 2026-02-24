"""Unit tests for GitRepository branch operations.

These tests use real GitPython repos in temp directories to verify
GitRepository correctly wraps GitPython Repo operations.
"""

import os
import subprocess
import tempfile

import pytest
from git import Repo

from i2code.implement.git_repository import GitRepository
from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestHeadSha:

    def test_returns_current_head_commit_sha(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        assert git_repo.head_sha == repo.head.commit.hexsha


@pytest.mark.unit
class TestHeadAdvancedSince:

    def test_returns_false_when_head_unchanged(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        original = git_repo.head_sha
        assert git_repo.head_advanced_since(original) is False

    def test_returns_true_after_new_commit(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

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
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        result = git_repo.ensure_branch("feature/new-branch")

        assert result == "feature/new-branch"
        assert "feature/new-branch" in [b.name for b in repo.branches]

    def test_reuses_existing_branch(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        repo.create_head("feature/existing")
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

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

        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        result = git_repo.ensure_branch("idea/test/01-setup", from_ref="idea/test/integration")

        assert result == "idea/test/01-setup"
        # New branch should point to integration branch commit, not master
        new_branch_sha = repo.heads["idea/test/01-setup"].commit.hexsha
        integration_sha = repo.heads["idea/test/integration"].commit.hexsha
        assert new_branch_sha == integration_sha


@pytest.mark.unit
class TestEnsureIdeaBranch:

    def test_creates_idea_branch_from_head(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        result = git_repo.ensure_idea_branch("my-feature")

        assert result == "idea/my-feature"
        assert "idea/my-feature" in [b.name for b in repo.branches]

    def test_reuses_existing_idea_branch(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        repo.create_head("idea/my-feature")
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        result = git_repo.ensure_idea_branch("my-feature")

        assert result == "idea/my-feature"
        matching = [b for b in repo.branches if b.name == "idea/my-feature"]
        assert len(matching) == 1


@pytest.mark.unit
class TestCheckout:

    def test_checks_out_branch(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        repo.create_head("feature/checkout-test")
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

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
            git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
            wt_repo = git_repo.ensure_worktree("test-idea", "feature/wt-test")

            assert isinstance(wt_repo, GitRepository)
            expected = os.path.join(parent_dir, "my-repo-wt-test-idea")
            assert wt_repo.working_tree_dir == expected
            assert os.path.isdir(wt_repo.working_tree_dir)

    def test_reuses_existing_worktree(self):
        with tempfile.TemporaryDirectory() as parent:
            repo, _ = _named_repo_with_branch(parent, "feature/wt-reuse")
            git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
            wt1 = git_repo.ensure_worktree("reuse-idea", "feature/wt-reuse")
            wt2 = git_repo.ensure_worktree("reuse-idea", "feature/wt-reuse")

            assert wt1.working_tree_dir == wt2.working_tree_dir


@pytest.mark.unit
class TestWorkingTreeDir:

    def test_returns_repo_working_tree_dir(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        assert git_repo.working_tree_dir == repo.working_tree_dir


@pytest.mark.unit
class TestBranchState:

    def test_branch_is_none_by_default(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        assert git_repo.branch is None

    def test_branch_tracks_value_set(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        git_repo.branch = "idea/test/01-setup"

        assert git_repo.branch == "idea/test/01-setup"


@pytest.mark.unit
class TestPrNumberState:

    def test_pr_number_is_none_by_default(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        assert git_repo.pr_number is None

    def test_pr_number_tracks_value_set(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        git_repo.pr_number = 42

        assert git_repo.pr_number == 42


@pytest.mark.unit
class TestPush:

    def test_push_delegates_to_subprocess_with_tracked_branch(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        git_repo.branch = "idea/test/01-setup"

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        result = git_repo.push()

        assert result is True
        mock_run.assert_called_once_with(
            ["git", "push", "-u", "origin", "idea/test/01-setup"],
            capture_output=True, text=True,
        )

    def test_push_returns_false_on_failure(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        git_repo.branch = "idea/test/01-setup"

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")

        result = git_repo.push()

        assert result is False


@pytest.mark.unit
class TestEnsurePr:

    def test_reuses_existing_pr(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        gh = FakeGitHubClient()
        gh.set_pr_list([{"number": 42, "headRefName": "idea/test", "isDraft": True}])

        git_repo = GitRepository(repo, gh_client=gh)
        git_repo.branch = "idea/test"

        result = git_repo.ensure_pr(
            idea_directory="/fake/idea",
            idea_name="test",
        )

        assert result == 42
        assert git_repo.pr_number == 42

    def test_creates_new_pr_when_none_exists(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        gh = FakeGitHubClient()
        gh.set_next_pr_number(99)

        git_repo = GitRepository(repo, gh_client=gh)
        git_repo.branch = "idea/test"

        result = git_repo.ensure_pr(
            idea_directory="/fake/idea",
            idea_name="test",
        )

        assert result == 99
        assert git_repo.pr_number == 99

    def test_creates_pr_with_title_from_idea_file(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        # Create idea directory with idea file
        idea_dir = os.path.join(tmpdir, "test-idea")
        os.makedirs(idea_dir)
        idea_file = os.path.join(idea_dir, "test-idea-name-idea.md")
        with open(idea_file, "w") as f:
            f.write("# My Test Idea\n\nDescription.\n")

        gh = FakeGitHubClient()
        gh.set_next_pr_number(99)

        git_repo = GitRepository(repo, gh_client=gh)
        git_repo.branch = "idea/test-idea-name"

        git_repo.ensure_pr(
            idea_directory=idea_dir,
            idea_name="test-idea-name",
        )

        # Check the PR was created with title from the idea file heading
        create_calls = [c for c in gh.calls if c[0] == "create_draft_pr"]
        assert len(create_calls) == 1
        _, branch, title, body, base = create_calls[0]
        assert title == "My Test Idea"
        assert body == f"**Idea directory:** `{idea_dir}`"

    def test_returns_cached_pr_number_on_second_call(self, test_git_repo_with_commit):
        tmpdir, repo = test_git_repo_with_commit
        gh = FakeGitHubClient()
        gh.set_next_pr_number(99)

        git_repo = GitRepository(repo, gh_client=gh)
        git_repo.branch = "idea/test"

        git_repo.ensure_pr(
            idea_directory="/fake/idea",
            idea_name="test",
        )
        # Second call should return cached value without calling gh again
        result = git_repo.ensure_pr(
            idea_directory="/fake/idea",
            idea_name="test",
        )

        assert result == 99
        # Only one find_pr call (first time); second time pr_number is already set
        find_calls = [c for c in gh.calls if c[0] == "find_pr"]
        assert len(find_calls) == 1


@pytest.mark.unit
class TestDiffFileAgainstHead:

    def test_returns_diff_output(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="diff --git a/plan.md b/plan.md\n-old\n+new\n",
            stderr="",
        )

        result = git_repo.diff_file_against_head("/some/path/plan.md")

        assert result == "diff --git a/plan.md b/plan.md\n-old\n+new\n"
        mock_run.assert_called_once_with(
            ["git", "diff", "HEAD", "--", "/some/path/plan.md"],
            capture_output=True, text=True,
            cwd=repo.working_tree_dir,
        )

    def test_returns_empty_string_when_no_changes(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )

        result = git_repo.diff_file_against_head("/some/path/plan.md")

        assert result == ""


@pytest.mark.unit
class TestShowFileAtHead:

    def test_returns_file_content(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        file_path = os.path.join(tmpdir, "docs", "plan.md")

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="# Plan\n- [ ] Task 1\n",
            stderr="",
        )

        result = git_repo.show_file_at_head(file_path)

        assert result == "# Plan\n- [ ] Task 1\n"
        mock_run.assert_called_once_with(
            ["git", "show", "HEAD:docs/plan.md"],
            capture_output=True, text=True,
            cwd=repo.working_tree_dir,
        )


@pytest.mark.unit
class TestBranchHasBeenPushed:

    def test_returns_false_when_branch_not_on_remote(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        git_repo.branch = "idea/test/01-setup"

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        assert git_repo.branch_has_been_pushed() is False

    def test_returns_true_when_branch_on_remote(self, test_git_repo_with_commit, mocker):
        tmpdir, repo = test_git_repo_with_commit
        git_repo = GitRepository(repo, gh_client=FakeGitHubClient())
        git_repo.branch = "idea/test/01-setup"

        mock_run = mocker.patch("i2code.implement.git_repository.subprocess.run")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="abc123\trefs/heads/idea/test/01-setup",
            stderr="",
        )

        assert git_repo.branch_has_been_pushed() is True


