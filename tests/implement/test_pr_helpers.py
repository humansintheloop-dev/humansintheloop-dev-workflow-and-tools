"""Tests for PR helper functions in implement-with-worktree."""

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
class TestPushOperations:
    """Test push operations to slice branch."""

    def test_build_push_command(self):
        """Should build correct git push command."""
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup")

        assert cmd == ["git", "push", "origin", "idea/my-feature/01-setup"]

    def test_build_push_command_with_force(self):
        """Should include --force-with-lease when requested."""
        from i2code.implement.pr_helpers import build_push_command

        cmd = build_push_command("idea/my-feature/01-setup", force=True)

        assert "--force-with-lease" in cmd


@pytest.mark.unit
class TestPushToSliceBranch:
    """Test push_to_slice_branch function."""

    def test_push_returns_false_if_pr_not_draft(self, mocker):
        """Should not push and return False if PR is not in Draft state."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import push_to_slice_branch

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": False})
        # Mock subprocess.run to track if it was called
        mock_run = mocker.patch('i2code.implement.pr_helpers.subprocess.run')

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123,
            gh_client=fake,
        )

        assert result is False
        mock_run.assert_not_called()

    def test_push_succeeds_when_pr_is_draft(self, mocker):
        """Should push and return True when PR is in Draft state."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import push_to_slice_branch

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": True})
        # Mock subprocess.run to simulate successful push
        mock_run = mocker.patch('i2code.implement.pr_helpers.subprocess.run')
        mock_run.return_value.returncode = 0

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123,
            gh_client=fake,
        )

        assert result is True
        mock_run.assert_called_once()

    def test_push_returns_false_on_push_failure(self, mocker):
        """Should return False when git push fails."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import push_to_slice_branch

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": True})
        # Mock subprocess.run to simulate failed push
        mock_run = mocker.patch('i2code.implement.pr_helpers.subprocess.run')
        mock_run.return_value.returncode = 1

        result = push_to_slice_branch(
            slice_branch="idea/my-feature/01-setup",
            pr_number=123,
            gh_client=fake,
        )

        assert result is False


@pytest.mark.unit
class TestPRReadyForReview:
    """Test marking PR as ready for review."""

    def test_mark_pr_ready_calls_gh_pr_ready(self, mocker):
        """Should call gh pr ready with PR number."""
        from i2code.implement.pr_helpers import mark_pr_ready

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0

        result = mark_pr_ready(123)

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gh" in call_args
        assert "pr" in call_args
        assert "ready" in call_args
        assert "123" in call_args

    def test_mark_pr_ready_returns_false_on_failure(self, mocker):
        """Should return False when gh pr ready fails."""
        from i2code.implement.pr_helpers import mark_pr_ready

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 1

        result = mark_pr_ready(123)

        assert result is False


@pytest.mark.unit
class TestPRPolling:
    """Test PR polling for feedback."""

    def test_get_pr_state_returns_open(self, mocker):
        """Should return PR state from GitHub."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "OPEN"}'

        state = get_pr_state(123)

        assert state == "OPEN"

    def test_get_pr_state_returns_merged(self, mocker):
        """Should return MERGED state when PR is merged."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "MERGED"}'

        state = get_pr_state(123)

        assert state == "MERGED"

    def test_get_pr_state_returns_closed(self, mocker):
        """Should return CLOSED state when PR is closed."""
        from i2code.implement.pr_helpers import get_pr_state

        mock_run = mocker.patch('i2code.implement.github_client.subprocess.run')
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"state": "CLOSED"}'

        state = get_pr_state(123)

        assert state == "CLOSED"

    def test_is_pr_complete_true_when_merged(self):
        """Should return True when PR is merged."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("MERGED") is True

    def test_is_pr_complete_true_when_closed(self):
        """Should return True when PR is closed."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("CLOSED") is True

    def test_is_pr_complete_false_when_open(self):
        """Should return False when PR is still open."""
        from i2code.implement.pr_helpers import is_pr_complete

        assert is_pr_complete("OPEN") is False


@pytest.mark.unit
class TestSliceRollover:
    """Test slice rollover when PR exits Draft state unexpectedly."""

    def test_should_rollover_true_when_not_draft_with_local_commits(self):
        """Should return True when PR is not draft and has unpushed commits."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import should_rollover

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": False})

        result = should_rollover(pr_number=123, has_unpushed_commits=True, gh_client=fake)

        assert result is True

    def test_should_rollover_false_when_draft(self):
        """Should return False when PR is still in draft state."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import should_rollover

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": True})

        result = should_rollover(pr_number=123, has_unpushed_commits=True, gh_client=fake)

        assert result is False

    def test_should_rollover_false_when_no_unpushed_commits(self):
        """Should return False when there are no unpushed commits."""
        from fake_github_client import FakeGitHubClient
        from i2code.implement.pr_helpers import should_rollover

        fake = FakeGitHubClient()
        fake.set_pr_view(123, {"isDraft": False})

        result = should_rollover(pr_number=123, has_unpushed_commits=False, gh_client=fake)

        assert result is False

    def test_generate_next_slice_branch_increments_number(self):
        """Should generate next slice branch with incremented number."""
        from i2code.implement.pr_helpers import generate_next_slice_branch

        next_branch = generate_next_slice_branch(
            idea_name="my-feature",
            current_slice_number=1,
            slice_name="continuation"
        )

        assert next_branch == "idea/my-feature/02-continuation"

    def test_generate_next_slice_branch_zero_pads(self):
        """Should zero-pad the slice number."""
        from i2code.implement.pr_helpers import generate_next_slice_branch

        next_branch = generate_next_slice_branch(
            idea_name="my-feature",
            current_slice_number=9,
            slice_name="next"
        )

        assert next_branch == "idea/my-feature/10-next"
