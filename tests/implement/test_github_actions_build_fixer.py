"""Tests for GithubActionsBuildFixer class."""

import pytest

from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.implement_opts import ImplementOpts

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
            [{"name": "CI", "conclusion": "failure"}],
        )

        def fix_and_advance(**kwargs):
            fake_repo.calls.append(("fix_ci_failure", kwargs.get("worktree_path")))
            fake_repo.set_head_sha("bbb")
            return True

        fake_repo.fix_ci_failure = fix_and_advance

        opts = ImplementOpts(idea_directory="/fake/idea")
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo)

        assert fixer.check_and_fix_ci() is True

        # fix_ci_failure was called on git_repo
        assert any(c[0] == "fix_ci_failure" for c in fake_repo.calls)
        captured = capsys.readouterr()
        assert "CI build failing" in captured.out

    def test_exits_when_ci_fix_fails(self):
        fake_gh = FakeGitHubClient()
        fake_repo = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_repo.set_pushed(True)
        fake_repo.branch = "idea/test/01-setup"

        def fix_fails(**kwargs):
            fake_repo.calls.append(("fix_ci_failure",))
            return False

        fake_repo.fix_ci_failure = fix_fails
        fake_gh.set_workflow_runs(
            "idea/test/01-setup", "aaa",
            [{"name": "CI", "conclusion": "failure"}],
        )

        opts = ImplementOpts(idea_directory="/fake/idea")
        fixer = GithubActionsBuildFixer(opts=opts, git_repo=fake_repo)

        with pytest.raises(SystemExit) as exc_info:
            fixer.check_and_fix_ci()

        assert exc_info.value.code == 1
