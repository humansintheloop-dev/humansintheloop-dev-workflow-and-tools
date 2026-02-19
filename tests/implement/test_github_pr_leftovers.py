"""Tests for GitHub PR management in implement-with-worktree."""

import pytest


@pytest.mark.unit
class TestPRTitleGeneration:
    """Test PR title generation from slice name."""

    def test_generate_pr_title(self):
        """Should generate PR title from idea and slice name."""
        from i2code.implement.pr_helpers import generate_pr_title

        title = generate_pr_title("my-feature", "01-project-setup")
        assert title == "[my-feature] 01-project-setup"

    def test_generate_pr_title_preserves_slice_name(self):
        """PR title should preserve the full slice name."""
        from i2code.implement.pr_helpers import generate_pr_title

        title = generate_pr_title("wt-pr-based-development", "03-feedback-handling")
        assert title == "[wt-pr-based-development] 03-feedback-handling"


@pytest.mark.unit
class TestPRBodyGeneration:
    """Test PR body generation."""

    def test_generate_pr_body(self):
        """Should generate PR body with idea directory reference."""
        from i2code.implement.pr_helpers import generate_pr_body

        body = generate_pr_body(
            idea_directory="docs/features/my-feature",
            idea_name="my-feature",
            slice_number=1
        )

        assert "docs/features/my-feature" in body
        assert "my-feature" in body
        assert "slice 1" in body.lower() or "slice #1" in body.lower()


@pytest.mark.unit
class TestEnsurePrOnGitRepository:
    """Test GitRepository.ensure_pr() orchestration with FakeGitHubClient."""

    def test_ensure_pr_raises_on_creation_failure(self, test_git_repo_with_commit):
        """ensure_pr should raise when PR creation fails."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        class FailingFakeClient(FakeGitHubClient):
            def create_draft_pr(self, *args, **kwargs):
                raise RuntimeError("PR creation failed")

        tmpdir, repo = test_git_repo_with_commit
        fake = FailingFakeClient()
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        with pytest.raises(RuntimeError):
            git_repo.ensure_pr("/path/to/idea", "test", 1)

    def test_ensure_pr_uses_default_branch_from_gh_client(self, test_git_repo_with_commit):
        """ensure_pr should fetch default branch from gh_client."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_next_pr_number(42)
        fake.set_default_branch("develop")
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        git_repo.ensure_pr("/path/to/idea", "test", 1)

        assert len(fake._created_prs) == 1
        assert fake._created_prs[0]["base"] == "develop"

    def test_ensure_pr_reuses_existing_pr(self, test_git_repo_with_commit):
        """ensure_pr should return existing PR number if one exists."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.git_repository import GitRepository

        tmpdir, repo = test_git_repo_with_commit
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 77, "headRefName": "idea/test/01-setup"}])
        git_repo = GitRepository(repo, gh_client=fake)
        git_repo.branch = "idea/test/01-setup"

        result = git_repo.ensure_pr("/path/to/idea", "test", 1)

        assert result == 77
        assert len(fake._created_prs) == 0


