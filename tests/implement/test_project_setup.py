"""Tests for project scaffolding setup."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

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
    """Test run_scaffolding() exits on Claude failure."""

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_non_zero_exit_code_exits(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(returncode=1, stdout="", stderr="", error_message="Something broke")

        with pytest.raises(SystemExit) as exc_info:
            run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_no_success_tag_exits(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(returncode=0, stdout="no tag here", stderr="")

        with pytest.raises(SystemExit) as exc_info:
            run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_failure_prints_permission_denials(self, mock_build, mock_run, capsys):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(
            returncode=0, stdout="<FAILURE>no perms</FAILURE>", stderr="",
            permission_denials=[{"tool_name": "Bash", "tool_input": {"command": "git commit"}}],
        )

        with pytest.raises(SystemExit):
            run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "Permission denied" in captured.err

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_failure_prints_last_messages(self, mock_build, mock_run, capsys):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(
            returncode=1, stdout="", stderr="",
            last_messages=[
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "I cannot write files"}]}},
                {"type": "result", "result": "No permissions to complete task"},
            ],
        )

        with pytest.raises(SystemExit):
            run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "I cannot write files" in captured.err
        assert "No permissions to complete task" in captured.err

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_success_tag_does_not_exit(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(
            returncode=0, stdout="...<SUCCESS>Scaffold created</SUCCESS>...", stderr=""
        )

        run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_interactive_mode_does_not_check_stdout(self, mock_build, mock_run):
        """Interactive mode has empty stdout — should not exit."""
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "prompt"]
        mock_run.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)


@pytest.mark.unit
class TestEnsureProjectSetup:
    """Test ensure_project_setup() orchestration."""

    def _make_claude_result(self, returncode=0, stdout="<SUCCESS>Scaffold created</SUCCESS>"):
        return ClaudeResult(returncode=returncode, stdout=stdout, stderr="")

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_checks_out_integration_branch(
        self, mock_build_prompt, mock_run_claude, mock_push
    ):
        """Should checkout integration branch before invoking Claude."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_gh = MagicMock()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            gh_client=mock_gh,
        )

        mock_repo.git.checkout.assert_called_with("idea/test/integration")

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_interactive_calls_run_claude_interactive(
        self, mock_build_prompt, mock_run_claude, mock_push
    ):
        """Interactive mode should use run_claude_interactive."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_gh = MagicMock()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=True,
            gh_client=mock_gh,
        )

        mock_run_claude.assert_called_once_with(["claude", "prompt"], cwd="/tmp/fake-repo")

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_non_interactive_calls_output_capture(
        self, mock_build_prompt, mock_run_capture, mock_push
    ):
        """Non-interactive mode should use run_claude_with_output_capture."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "-p", "prompt"]
        mock_run_capture.return_value = self._make_claude_result()
        mock_gh = MagicMock()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=False,
            gh_client=mock_gh,
        )

        mock_run_capture.assert_called_once_with(["claude", "-p", "prompt"], cwd="/tmp/fake-repo")

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_no_new_commits_skips_push_and_ci(
        self, mock_build_prompt, mock_run_claude, mock_push
    ):
        """When Claude makes no commits, should skip push and CI, return True."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_gh = MagicMock()

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            gh_client=mock_gh,
        )

        assert result is True
        mock_push.assert_not_called()
        mock_gh.wait_for_workflow_completion.assert_not_called()

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_push_and_ci_when_commits_made(
        self, mock_build_prompt, mock_run_claude, mock_push
    ):
        """When Claude makes commits, should push and wait for CI."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        commit_before = MagicMock()
        commit_before.hexsha = "aaa111"
        commit_after = MagicMock()
        commit_after.hexsha = "bbb222"
        type(mock_repo.head).commit = PropertyMock(side_effect=[commit_before, commit_after])
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_push.return_value = True
        mock_gh = MagicMock()
        mock_gh.wait_for_workflow_completion.return_value = (True, None)

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            ci_timeout=300,
            gh_client=mock_gh,
        )

        assert result is True
        mock_push.assert_called_once_with("idea/test/integration")
        mock_gh.wait_for_workflow_completion.assert_called_once_with(
            "idea/test/integration", "bbb222", timeout_seconds=300
        )

    @patch("i2code.implement.github_actions_build_fixer.GithubActionsBuildFixer.fix_ci_failure")
    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_ci_failure_retry_success(
        self, mock_build_prompt, mock_run_capture, mock_push, mock_fix_ci
    ):
        """When CI fails, should construct GithubActionsBuildFixer and call fix_ci_failure."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        commit_before = MagicMock()
        commit_before.hexsha = "aaa111"
        commit_after = MagicMock()
        commit_after.hexsha = "bbb222"
        type(mock_repo.head).commit = PropertyMock(side_effect=[commit_before, commit_after])
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "-p", "prompt"]
        mock_run_capture.return_value = self._make_claude_result()
        mock_push.return_value = True
        mock_gh = MagicMock()
        mock_gh.wait_for_workflow_completion.return_value = (False, {"name": "CI", "id": 123})
        mock_fix_ci.return_value = True

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=False,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            gh_client=mock_gh,
        )

        assert result is True
        mock_fix_ci.assert_called_once()

    @patch("i2code.implement.github_actions_build_fixer.GithubActionsBuildFixer.fix_ci_failure")
    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_ci_failure_retry_fails(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_fix_ci
    ):
        """When CI fails and fix_ci_failure also fails, should return False."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        commit_before = MagicMock()
        commit_before.hexsha = "aaa111"
        commit_after = MagicMock()
        commit_after.hexsha = "bbb222"
        type(mock_repo.head).commit = PropertyMock(side_effect=[commit_before, commit_after])
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_push.return_value = True
        mock_gh = MagicMock()
        mock_gh.wait_for_workflow_completion.return_value = (False, {"name": "CI", "id": 123})
        mock_fix_ci.return_value = False

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            gh_client=mock_gh,
        )

        assert result is False

    @patch("i2code.implement.project_setup.push_branch_to_remote")
    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_ensure_project_setup_skip_ci_wait_pushes_but_no_wait(
        self, mock_build_prompt, mock_run_claude, mock_push
    ):
        """When skip_ci_wait=True and commits made, should push but not wait for CI."""
        from i2code.implement.project_setup import ensure_project_setup

        mock_repo = MagicMock()
        commit_before = MagicMock()
        commit_before.hexsha = "aaa111"
        commit_after = MagicMock()
        commit_after.hexsha = "bbb222"
        type(mock_repo.head).commit = PropertyMock(side_effect=[commit_before, commit_after])
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_push.return_value = True
        mock_gh = MagicMock()

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            skip_ci_wait=True,
            gh_client=mock_gh,
        )

        assert result is True
        mock_push.assert_called_once_with("idea/test/integration")
        mock_gh.wait_for_workflow_completion.assert_not_called()


@pytest.mark.unit
class TestRunScaffolding:
    """Test run_scaffolding() delegates to correct runner."""

    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_interactive_calls_run_claude_interactive(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "prompt"]
        mock_run.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)

        mock_build.assert_called_once_with("/tmp/idea", interactive=True, mock_claude=None)
        mock_run.assert_called_once_with(["claude", "prompt"], cwd="/tmp/repo")

    @patch("i2code.implement.project_setup.run_claude_with_output_capture")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_non_interactive_calls_output_capture(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["claude", "-p", "prompt"]
        mock_run.return_value = ClaudeResult(
            returncode=0, stdout="<SUCCESS>Scaffold created</SUCCESS>", stderr=""
        )

        run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        mock_build.assert_called_once_with("/tmp/idea", interactive=False, mock_claude=None)
        mock_run.assert_called_once_with(["claude", "-p", "prompt"], cwd="/tmp/repo")

    @patch("i2code.implement.project_setup.run_claude_interactive")
    @patch("i2code.implement.project_setup.CommandBuilder.build_scaffolding_command")
    def test_forwards_mock_claude(self, mock_build, mock_run):
        from i2code.implement.project_setup import run_scaffolding

        mock_build.return_value = ["/mock.sh", "setup"]
        mock_run.return_value = ClaudeResult(returncode=0, stdout="", stderr="")

        run_scaffolding("/tmp/idea", cwd="/tmp/repo", mock_claude="/mock.sh")

        mock_build.assert_called_once_with("/tmp/idea", interactive=True, mock_claude="/mock.sh")


@pytest.mark.unit
class TestScaffoldCmd:
    """Test scaffold CLI command."""

    @patch("i2code.implement.cli.run_scaffolding")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_validates_and_invokes_run_scaffolding(
        self, mock_repo_cls, mock_idea_project_cls, mock_run_scaffolding
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
        mock_run_scaffolding.assert_called_once_with(
            "/tmp/fake-idea",
            cwd="/tmp/fake-repo",
            interactive=True,
            mock_claude=None,
        )

    @patch("i2code.implement.cli.run_scaffolding")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_non_interactive_forwards_flag(
        self, mock_repo_cls, mock_idea_project_cls, mock_run_scaffolding
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
        call_kwargs = mock_run_scaffolding.call_args[1]
        assert call_kwargs["interactive"] is False

    @patch("i2code.implement.cli.run_scaffolding")
    @patch("i2code.implement.cli.IdeaProject")
    @patch("i2code.implement.cli.Repo")
    def test_scaffold_forwards_mock_claude(
        self, mock_repo_cls, mock_idea_project_cls, mock_run_scaffolding
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
        call_kwargs = mock_run_scaffolding.call_args[1]
        assert call_kwargs["mock_claude"] == "/mock.sh"


