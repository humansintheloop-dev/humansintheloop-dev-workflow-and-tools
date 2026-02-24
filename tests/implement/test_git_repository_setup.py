"""Tests for Git repository setup: idea branches, worktrees."""

import os
import tempfile
import pytest

from git import Repo

from i2code.implement.git_repository import GitRepository
from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestWorktree:
    """Test worktree creation details (naming, settings copy)."""

    def test_worktree_naming_pattern(self):
        """Worktree path should follow ../<repo-name>-wt-<idea-name> pattern."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo with specific name
            repo_path = os.path.join(tmpdir, "genai-development-workflow")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create idea branch
            idea_branch = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_idea_branch("wt-pr-based-development")

            # Create worktree
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("wt-pr-based-development", idea_branch)

            expected_path = os.path.join(tmpdir, "genai-development-workflow-wt-wt-pr-based-development")
            assert wt_repo.working_tree_dir == expected_path

    def test_does_not_fail_if_settings_local_json_missing(self):
        """Should not fail if .claude/settings.local.json does not exist."""

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo WITHOUT .claude/settings.local.json
            repo_path = os.path.join(tmpdir, "my-repo")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create idea branch and worktree - should not fail
            idea_branch = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_idea_branch("my-feature")
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", idea_branch)

            # Worktree should exist
            assert os.path.isdir(wt_repo.working_tree_dir)


@pytest.mark.unit
class TestSliceNameSanitization:
    """Test sanitizing task names for branch names."""

    def test_sanitize_simple_name(self):
        """Simple names should pass through with lowercase."""

        assert GitRepository.sanitize_branch_name("Project Setup") == "project-setup"

    def test_sanitize_removes_special_chars(self):
        """Special characters should be removed or replaced."""

        assert GitRepository.sanitize_branch_name("Task 1.1: Create files") == "task-1-1-create-files"

    def test_sanitize_collapses_multiple_dashes(self):
        """Multiple dashes should be collapsed to one."""

        assert GitRepository.sanitize_branch_name("foo---bar") == "foo-bar"

    def test_sanitize_strips_leading_trailing_dashes(self):
        """Leading and trailing dashes should be stripped."""

        assert GitRepository.sanitize_branch_name("--foo-bar--") == "foo-bar"


@pytest.mark.unit
class TestEnsurePrOnGitRepository:
    """Test GitRepository.ensure_pr() orchestration with FakeGitHubClient."""

    def test_ensure_pr_raises_on_creation_failure(self, test_git_repo_with_commit):
        """ensure_pr should raise when PR creation fails."""
        from fake_github_client import FakeGitHubClient as _FakeGitHubClient

        class FailingFakeClient(_FakeGitHubClient):
            def create_draft_pr(self, *args, **kwargs):
                raise RuntimeError("PR creation failed")

        tmpdir, repo = test_git_repo_with_commit
        fake = FailingFakeClient()
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        with pytest.raises(RuntimeError):
            git_repo.ensure_pr("/path/to/idea", "test")

    def test_ensure_pr_uses_default_branch_from_gh_client(self, test_git_repo_with_commit):
        """ensure_pr should fetch default branch from gh_client."""

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_next_pr_number(42)
        fake.set_default_branch("develop")
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        git_repo.ensure_pr("/path/to/idea", "test")

        assert len(fake._created_prs) == 1
        assert fake._created_prs[0]["base"] == "develop"

    def test_ensure_pr_reuses_existing_pr(self, test_git_repo_with_commit):
        """ensure_pr should return existing PR number if one exists."""

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 77, "headRefName": "idea/test/01-setup"}])
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        result = git_repo.ensure_pr("/path/to/idea", "test")

        assert result == 77
        assert len(fake._created_prs) == 0
