"""Tests for GithubActionsBuildFixer class."""

import pytest

from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.implement_opts import ImplementOpts

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient


@pytest.mark.unit
class TestGithubActionsBuildFixerCheckAndFixCi:
    """GithubActionsBuildFixer.check_and_fix_ci() detects and fixes CI failures."""

    def test_returns_false_when_branch_not_pushed(self):
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo")
        # pushed is False by default
        opts = ImplementOpts(idea_directory="/fake/idea")
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo)

        assert fixer.check_and_fix_ci() is False

    def test_returns_false_when_no_failing_run(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        fake_repo.branch = "idea/test/01-setup"
        # No workflow runs set → no failing run found
        opts = ImplementOpts(idea_directory="/fake/idea")
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo)

        assert fixer.check_and_fix_ci() is False

    def test_fixes_ci_failure_and_returns_true(self, capsys):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        fake_repo.branch = "idea/test/01-setup"
        fake_gh.set_workflow_runs(
            "idea/test/01-setup", "aaa",
            [{"databaseId": 42, "name": "CI", "conclusion": "failure"}],
        )
        fake_gh.set_workflow_failure_logs(42, "Build failed")

        fake_runner = FakeClaudeRunner()
        fake_runner.set_side_effect(lambda: fake_repo.set_head_sha("bbb"))
        fake_gh.set_workflow_completion_result("idea/test/01-setup", "bbb", (True, None))

        opts = ImplementOpts(idea_directory="/fake/idea", non_interactive=True)
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo, claude_runner=fake_runner)

        assert fixer.check_and_fix_ci() is True

        captured = capsys.readouterr()
        assert "CI build failing" in captured.out

    def test_exits_when_ci_fix_fails(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        fake_repo.branch = "idea/test/01-setup"
        fake_gh.set_workflow_runs(
            "idea/test/01-setup", "aaa",
            [{"databaseId": 42, "name": "CI", "conclusion": "failure"}],
        )
        fake_gh.set_workflow_failure_logs(42, "Build failed")

        fake_runner = FakeClaudeRunner()
        # Claude makes no commits → head_sha stays "aaa" → fix_ci_failure returns False

        opts = ImplementOpts(idea_directory="/fake/idea", ci_fix_retries=1, non_interactive=True)
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo, claude_runner=fake_runner)

        with pytest.raises(SystemExit) as exc_info:
            fixer.check_and_fix_ci()

        assert exc_info.value.code == 1


@pytest.mark.unit
class TestGithubActionsBuildFixerFixCiFailure:
    """GithubActionsBuildFixer.fix_ci_failure() attempts to fix CI failures."""

    def test_returns_true_when_no_failing_run(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.branch = "idea/test/01-setup"
        fake_runner = FakeClaudeRunner()
        opts = ImplementOpts(idea_directory="/fake/idea")
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo, claude_runner=fake_runner)

        result = fixer.fix_ci_failure()

        assert result is True

    def test_returns_false_when_claude_makes_no_commit(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.branch = "idea/test/01-setup"
        fake_repo.set_head_sha("aaa")
        fake_gh.set_workflow_runs(
            "idea/test/01-setup", "aaa",
            [{"databaseId": 123, "name": "CI Build", "conclusion": "failure"}],
        )
        fake_gh.set_workflow_failure_logs(123, "Build failed: compilation error")

        fake_runner = FakeClaudeRunner()
        # Claude makes no commits → head_sha stays "aaa"
        opts = ImplementOpts(idea_directory="/fake/idea", ci_fix_retries=1, non_interactive=True)
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo, claude_runner=fake_runner)

        result = fixer.fix_ci_failure()

        assert result is False
        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "run_with_capture"

    def test_pushes_and_returns_true_when_ci_passes(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.branch = "idea/test/01-setup"
        fake_repo.set_head_sha("aaa")
        fake_gh.set_workflow_runs(
            "idea/test/01-setup", "aaa",
            [{"databaseId": 123, "name": "CI Build", "conclusion": "failure"}],
        )
        fake_gh.set_workflow_failure_logs(123, "Build failed")

        fake_runner = FakeClaudeRunner()
        # Simulate Claude making a commit by advancing head_sha
        fake_runner.set_side_effect(lambda: fake_repo.set_head_sha("bbb"))

        fake_gh.set_workflow_completion_result("idea/test/01-setup", "bbb", (True, None))

        opts = ImplementOpts(idea_directory="/fake/idea", ci_fix_retries=1, non_interactive=True)
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo, claude_runner=fake_runner)

        result = fixer.fix_ci_failure()

        assert result is True
        assert ("push",) in fake_repo.calls
        assert ("get_workflow_failure_logs", 123) in fake_gh.calls
