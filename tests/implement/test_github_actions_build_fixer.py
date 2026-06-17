"""Tests for GithubActionsBuildFixer class."""

import pytest

from i2code.implement.claude_runner import ClaudeCodeCommand
from i2code.implement.command_builder import CiFixRequest, CommandBuilder
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.implement_opts import ImplementOpts

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient

_BRANCH = "idea/test/01-setup"


def _make_fixer(pushed=True, failing_run=None, opts_overrides=None):
    """Create a GithubActionsBuildFixer with common test defaults.

    Returns (fixer, fake_repo, fake_gh, fake_runner_or_None).
    """
    fake_gh = FakeGitHubClient()
    fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
    fake_repo.set_pushed(pushed)
    fake_repo.branch = _BRANCH

    if failing_run:
        fake_gh.set_workflow_runs(_BRANCH, "aaa", [failing_run])
        fake_gh.set_workflow_failure_logs(failing_run["databaseId"], "Build failed")

    fake_runner = FakeClaudeRunner()
    defaults = dict(idea_directory="/fake/idea")
    if opts_overrides:
        defaults.update(opts_overrides)

    fixer = GithubActionsBuildFixer(
        opts=ImplementOpts(**defaults), git_repo=fake_repo,
        claude_runner=fake_runner,
    )
    return fixer, fake_repo, fake_gh, fake_runner


_CI_FAILURE = {"databaseId": 42, "name": "CI", "conclusion": "failure"}
_CI_BUILD_FAILURE = {"databaseId": 123, "name": "CI Build", "conclusion": "failure"}


@pytest.mark.unit
class TestGithubActionsBuildFixerCheckAndFixCi:
    """GithubActionsBuildFixer.check_and_fix_ci() detects and fixes CI failures."""

    def test_returns_false_when_branch_not_pushed(self):
        fixer, _, _, _ = _make_fixer(pushed=False)
        assert fixer.check_and_fix_ci() is False

    def test_returns_false_when_no_failing_run(self):
        fixer, _, _, _ = _make_fixer()
        assert fixer.check_and_fix_ci() is False

    def test_fixes_ci_failure_and_returns_true(self, capsys):
        fixer, fake_repo, fake_gh, fake_runner = _make_fixer(
            failing_run=_CI_FAILURE, opts_overrides=dict(non_interactive=True),
        )
        fake_runner.set_side_effect(lambda: fake_repo.set_head_sha("bbb"))
        fake_gh.set_workflow_completion_result(_BRANCH, "bbb", (True, None))

        assert fixer.check_and_fix_ci() is True
        assert "CI build failing" in capsys.readouterr().out

    def test_exits_when_ci_fix_fails(self):
        fixer, _, _, _ = _make_fixer(
            failing_run=_CI_FAILURE, opts_overrides=dict(ci_fix_retries=1, non_interactive=True),
        )
        with pytest.raises(SystemExit) as exc_info:
            fixer.check_and_fix_ci()
        assert exc_info.value.code == 1


@pytest.mark.unit
class TestGithubActionsBuildFixerFixCiFailure:
    """GithubActionsBuildFixer.fix_ci_failure() attempts to fix CI failures."""

    def test_returns_true_when_no_failing_run(self):
        fixer, _, _, _ = _make_fixer()
        assert fixer.fix_ci_failure() is True

    def test_returns_false_when_claude_makes_no_commit(self):
        fixer, fake_repo, _, fake_runner = _make_fixer(
            failing_run=_CI_BUILD_FAILURE, opts_overrides=dict(ci_fix_retries=1, non_interactive=True),
        )
        fake_repo.set_head_sha("aaa")

        assert fixer.fix_ci_failure() is False
        assert len(fake_runner.calls) == 1
        assert fake_runner.calls[0][0] == "execute"

    def test_pushes_and_returns_true_when_ci_passes(self):
        fixer, fake_repo, fake_gh, fake_runner = _make_fixer(
            failing_run=_CI_BUILD_FAILURE, opts_overrides=dict(ci_fix_retries=1, non_interactive=True),
        )
        fake_repo.set_head_sha("aaa")
        fake_runner.set_side_effect(lambda: fake_repo.set_head_sha("bbb"))
        fake_gh.set_workflow_completion_result(_BRANCH, "bbb", (True, None))

        assert fixer.fix_ci_failure() is True
        assert ("push",) in fake_repo.calls
        assert ("get_workflow_failure_logs", 123) in fake_gh.calls

    def test_fix_ci_invokes_execute_with_command_dataclass(self):
        """Non-mock CI fix dispatches execute() with CommandBuilder output."""
        fixer, fake_repo, _, fake_runner = _make_fixer(
            failing_run=_CI_BUILD_FAILURE,
            opts_overrides=dict(ci_fix_retries=1, non_interactive=True),
        )
        fake_repo.set_head_sha("aaa")

        fixer.fix_ci_failure()

        assert len(fake_runner.calls) == 1
        method, cmd, cwd = fake_runner.calls[0]
        assert method == "execute"
        assert isinstance(cmd, ClaudeCodeCommand)
        expected = CommandBuilder().build_ci_fix_command(
            CiFixRequest(
                run_id=123,
                workflow_name="CI Build",
                failure_logs="Build failed",
            ),
            cwd=fake_repo.working_tree_dir,
            interactive=False,
        )
        assert cmd == expected
        assert cwd == fake_repo.working_tree_dir

    def test_fix_ci_with_mock_claude_uses_execute_with_mock_command(self):
        """When mock_claude is set, execute() receives a ClaudeCodeCommand with mock_command."""
        mock_path = "/path/to/mock-claude"
        fixer, fake_repo, _, fake_runner = _make_fixer(
            failing_run=_CI_BUILD_FAILURE,
            opts_overrides=dict(
                ci_fix_retries=1, non_interactive=True, mock_claude=mock_path,
            ),
        )
        fake_repo.set_head_sha("aaa")

        fixer.fix_ci_failure()

        assert len(fake_runner.calls) == 1
        method, cmd, cwd = fake_runner.calls[0]
        assert method == "execute"
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == fake_repo.working_tree_dir
        assert cmd.mock_command == [mock_path, "fix-ci-123"]
        assert cwd == fake_repo.working_tree_dir
