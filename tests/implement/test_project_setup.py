"""Tests for project scaffolding setup."""

import pytest
from unittest.mock import patch, MagicMock

from i2code.implement.claude_runner import ClaudeResult


def _make_mock_project(name="test-feature", directory="/tmp/fake-idea"):
    """Create a MagicMock that behaves like an IdeaProject instance."""
    mock_project = MagicMock()
    mock_project.name = name
    mock_project.directory = directory
    mock_project.plan_file = f"{directory}/{name}-plan.md"
    mock_project.state_file = f"{directory}/{name}-wt-state.json"
    mock_project.validate.return_value = mock_project
    mock_project.validate_files.return_value = None
    return mock_project


@pytest.mark.unit
class TestBuildScaffoldingPrompt:
    """Test build_scaffolding_prompt() constructs correct Claude commands."""

    def test_interactive_mode_returns_claude_with_prompt(self):
        """Interactive mode should return ['claude', <prompt>]."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)

        assert cmd[0] == "claude"
        assert len(cmd) == 2
        # Second element is the prompt string
        assert isinstance(cmd[1], str)

    def test_non_interactive_mode_returns_claude_with_p_flag(self):
        """Non-interactive mode should return ['claude', '--verbose', '--output-format=stream-json', '-p', <prompt>]."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=False)

        assert cmd[0] == "claude"
        assert "--verbose" in cmd
        assert "--output-format=stream-json" in cmd
        assert "-p" in cmd
        # Prompt should be the last element (after -p)
        p_index = cmd.index("-p")
        assert p_index == len(cmd) - 2
        assert isinstance(cmd[p_index + 1], str)

    def test_prompt_references_idea_files(self):
        """Prompt should reference the idea directory files."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        assert "/tmp/docs/features/my-service" in prompt
        assert "*-idea.*" in prompt or "idea" in prompt.lower()
        assert "*-spec.md" in prompt or "spec" in prompt.lower()

    def test_prompt_describes_scaffolding_goals(self):
        """Prompt should describe desired scaffolding outcome without prescribing versions."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        # Should mention key scaffolding concepts
        assert "ci.yaml" in prompt.lower() or "ci" in prompt.lower()
        assert "scaffold" in prompt.lower() or "placeholder" in prompt.lower()
        assert "commit" in prompt.lower()

    def test_mock_claude_returns_mock_script_command(self):
        """When mock_claude is provided, should return [mock_script, 'setup']."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command(
            "/tmp/docs/features/my-service",
            mock_claude="/path/to/mock-claude.sh"
        )

        assert cmd == ["/path/to/mock-claude.sh", "setup"]

    def test_mock_claude_none_returns_normal_command(self):
        """When mock_claude is None, should return normal Claude command."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command(
            "/tmp/docs/features/my-service",
            mock_claude=None
        )

        assert cmd[0] == "claude"


@pytest.mark.unit
class TestRunScaffoldingFailure:
    """Test ProjectInitializer.run_scaffolding() exits on Claude failure."""

    def _make_initializer(self, fake):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectInitializer
        return ProjectInitializer(claude_runner=fake, command_builder=CommandBuilder())

    def test_non_zero_exit_code_exits(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=1, stdout="", stderr="", error_message="Something broke"))
        initializer = self._make_initializer(fake)

        with pytest.raises(SystemExit) as exc_info:
            initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    def test_no_success_tag_exits(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=0, stdout="no tag here", stderr=""))
        initializer = self._make_initializer(fake)

        with pytest.raises(SystemExit) as exc_info:
            initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    def test_failure_prints_permission_denials(self, capsys):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0, stdout="<FAILURE>no perms</FAILURE>", stderr="",
            permission_denials=[{"tool_name": "Bash", "tool_input": {"command": "git commit"}}],
        ))
        initializer = self._make_initializer(fake)

        with pytest.raises(SystemExit):
            initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "Permission denied" in captured.err

    def test_failure_prints_last_messages(self, capsys):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=1, stdout="", stderr="",
            last_messages=[
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "I cannot write files"}]}},
                {"type": "result", "result": "No permissions to complete task"},
            ],
        ))
        initializer = self._make_initializer(fake)

        with pytest.raises(SystemExit):
            initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "I cannot write files" in captured.err
        assert "No permissions to complete task" in captured.err

    def test_success_tag_does_not_exit(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0, stdout="...<SUCCESS>Scaffold created</SUCCESS>...", stderr=""
        ))
        initializer = self._make_initializer(fake)

        initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

    def test_interactive_mode_does_not_check_stdout(self):
        """Interactive mode has empty stdout — should not exit."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        initializer = self._make_initializer(fake)

        initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)


@pytest.mark.unit
class TestRunScaffolding:
    """Test ProjectInitializer.run_scaffolding() delegates to correct runner."""

    def test_interactive_calls_run_interactive(self):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectInitializer
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        initializer = ProjectInitializer(claude_runner=fake, command_builder=CommandBuilder())

        initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run_interactive"
        assert cmd[0] == "claude"
        assert cwd == "/tmp/repo"

    def test_non_interactive_calls_run_with_capture(self):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectInitializer
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0, stdout="<SUCCESS>Scaffold created</SUCCESS>", stderr=""
        ))
        initializer = ProjectInitializer(claude_runner=fake, command_builder=CommandBuilder())

        initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run_with_capture"
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert cwd == "/tmp/repo"

    def test_forwards_mock_claude(self):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectInitializer
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        initializer = ProjectInitializer(claude_runner=fake, command_builder=CommandBuilder())

        initializer.run_scaffolding("/tmp/idea", cwd="/tmp/repo", mock_claude="/mock.sh")

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run_interactive"
        assert cmd == ["/mock.sh", "setup"]


@pytest.mark.unit
class TestEnsureProjectSetupMethod:
    """Test ProjectInitializer.ensure_project_setup() with fakes — no @patch."""

    def _make_initializer(self, fake_runner=None, git_repo=None, build_fixer=None, push_fn=None):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectInitializer
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        return ProjectInitializer(
            claude_runner=fake_runner or FakeClaudeRunner(),
            command_builder=CommandBuilder(),
            git_repo=git_repo,
            build_fixer=build_fixer,
            push_fn=push_fn,
        )

    def test_no_new_commits_returns_true_without_pushing(self):
        """When scaffolding makes no commits, should return True without pushing."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository

        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo")
        fake_git.set_head_sha("abc123")
        pushed = []

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            push_fn=lambda branch: pushed.append(branch) or True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
        )

        assert result is True
        assert pushed == []

    def test_commits_made_pushes_and_waits_for_ci(self):
        """When scaffolding makes commits, should push and wait for CI."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_git.set_head_sha("aaa111")
        pushed = []

        def scaffolding_side_effect():
            fake_git.set_head_sha("bbb222")

        fake_runner.set_side_effect(scaffolding_side_effect)
        fake_gh.set_workflow_completion_result("idea/test/integration", "bbb222", (True, None))

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            push_fn=lambda branch: pushed.append(branch) or True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
            ci_timeout=300,
        )

        assert result is True
        assert pushed == ["idea/test/integration"]
        assert ("wait_for_workflow_completion", "idea/test/integration", "bbb222") in fake_gh.calls

    def test_skip_ci_wait_pushes_but_does_not_wait(self):
        """When skip_ci_wait=True, should push but not wait for CI."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_git.set_head_sha("aaa111")
        pushed = []

        def scaffolding_side_effect():
            fake_git.set_head_sha("bbb222")

        fake_runner.set_side_effect(scaffolding_side_effect)

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            push_fn=lambda branch: pushed.append(branch) or True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
            skip_ci_wait=True,
        )

        assert result is True
        assert pushed == ["idea/test/integration"]
        assert not any(call[0] == "wait_for_workflow_completion" for call in fake_gh.calls)

    def test_ci_failure_sets_branch_and_calls_build_fixer(self):
        """When CI fails, should set git_repo.branch and call build_fixer.fix_ci_failure()."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_git.set_head_sha("aaa111")

        def scaffolding_side_effect():
            fake_git.set_head_sha("bbb222")

        fake_runner.set_side_effect(scaffolding_side_effect)
        fake_gh.set_workflow_completion_result(
            "idea/test/integration", "bbb222", (False, {"name": "CI", "id": 123})
        )

        class FakeBuildFixer:
            def __init__(self):
                self.calls = []
                self.result = True

            def fix_ci_failure(self):
                self.calls.append("fix_ci_failure")
                return self.result

        fake_fixer = FakeBuildFixer()

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            build_fixer=fake_fixer,
            push_fn=lambda branch: True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
        )

        assert result is True
        assert fake_fixer.calls == ["fix_ci_failure"]
        assert fake_git.branch == "idea/test/integration"

    def test_ci_failure_fix_fails_returns_false(self):
        """When CI fails and fix_ci_failure returns False, should return False."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_git.set_head_sha("aaa111")

        def scaffolding_side_effect():
            fake_git.set_head_sha("bbb222")

        fake_runner.set_side_effect(scaffolding_side_effect)
        fake_gh.set_workflow_completion_result(
            "idea/test/integration", "bbb222", (False, {"name": "CI", "id": 123})
        )

        class FakeBuildFixer:
            def __init__(self):
                self.result = False

            def fix_ci_failure(self):
                return self.result

        fake_fixer = FakeBuildFixer()

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            build_fixer=fake_fixer,
            push_fn=lambda branch: True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
        )

        assert result is False

    def test_checkouts_integration_branch(self):
        """Should checkout the integration branch before scaffolding."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository

        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo")
        fake_git.set_head_sha("abc123")

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            push_fn=lambda branch: True,
        )

        initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
        )

        assert ("checkout", "idea/test/integration") in fake_git.calls

    def test_ci_failure_no_failing_run_returns_false(self):
        """When CI reports failure but no failing run, should return False."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir="/fake/repo", gh_client=fake_gh)
        fake_git.set_head_sha("aaa111")

        def scaffolding_side_effect():
            fake_git.set_head_sha("bbb222")

        fake_runner.set_side_effect(scaffolding_side_effect)
        fake_gh.set_workflow_completion_result(
            "idea/test/integration", "bbb222", (False, None)
        )

        initializer = self._make_initializer(
            fake_runner=fake_runner,
            git_repo=fake_git,
            push_fn=lambda branch: True,
        )

        result = initializer.ensure_project_setup(
            idea_directory="/tmp/idea",
            integration_branch="idea/test/integration",
        )

        assert result is False


@pytest.mark.unit
class TestScaffoldCmd:
    """Test scaffold CLI command."""

    @patch("i2code.implement.cli.ProjectInitializer")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_validates_and_invokes_run_scaffolding(
        self, mock_repo_cls, mock_idea_project_cls, mock_initializer_cls
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import scaffold_cmd

        mock_project = _make_mock_project()
        mock_idea_project_cls.return_value = mock_project
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(scaffold_cmd, ["/tmp/fake-idea"])

        assert result.exit_code == 0
        mock_project.validate.assert_called_once()
        mock_project.validate_files.assert_called_once()
        mock_initializer_cls.return_value.run_scaffolding.assert_called_once_with(
            "/tmp/fake-idea",
            cwd="/tmp/fake-repo",
            interactive=True,
            mock_claude=None,
        )

    @patch("i2code.implement.cli.ProjectInitializer")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_non_interactive_forwards_flag(
        self, mock_repo_cls, mock_idea_project_cls, mock_initializer_cls
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import scaffold_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(scaffold_cmd, ["/tmp/fake-idea", "--non-interactive"])

        assert result.exit_code == 0
        call_kwargs = mock_initializer_cls.return_value.run_scaffolding.call_args[1]
        assert call_kwargs["interactive"] is False

    @patch("i2code.implement.cli.ProjectInitializer")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_forwards_mock_claude(
        self, mock_repo_cls, mock_idea_project_cls, mock_initializer_cls
    ):
        from click.testing import CliRunner
        from i2code.implement.cli import scaffold_cmd

        mock_idea_project_cls.return_value = _make_mock_project()
        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner(catch_exceptions=False)
        result = runner.invoke(scaffold_cmd, ["/tmp/fake-idea", "--mock-claude", "/mock.sh"])

        assert result.exit_code == 0
        call_kwargs = mock_initializer_cls.return_value.run_scaffolding.call_args[1]
        assert call_kwargs["mock_claude"] == "/mock.sh"


