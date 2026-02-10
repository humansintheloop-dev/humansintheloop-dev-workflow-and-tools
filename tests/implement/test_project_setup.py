"""Tests for project scaffolding setup."""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from i2code.implement.implement import ClaudeResult


@pytest.mark.unit
class TestBuildScaffoldingPrompt:
    """Test build_scaffolding_prompt() constructs correct Claude commands."""

    def test_interactive_mode_returns_claude_with_prompt(self):
        """Interactive mode should return ['claude', <prompt>]."""
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt("/tmp/docs/features/my-service", interactive=True)

        assert cmd[0] == "claude"
        assert len(cmd) == 2
        # Second element is the prompt string
        assert isinstance(cmd[1], str)

    def test_non_interactive_mode_returns_claude_with_p_flag(self):
        """Non-interactive mode should return ['claude', '--verbose', '--output-format=stream-json', '-p', <prompt>]."""
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt("/tmp/docs/features/my-service", interactive=False)

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
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        assert "/tmp/docs/features/my-service" in prompt
        assert "*-idea.*" in prompt or "idea" in prompt.lower()
        assert "*-spec.md" in prompt or "spec" in prompt.lower()

    def test_prompt_describes_scaffolding_goals(self):
        """Prompt should describe desired scaffolding outcome without prescribing versions."""
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        # Should mention key scaffolding concepts
        assert "ci.yaml" in prompt.lower() or "ci" in prompt.lower()
        assert "scaffold" in prompt.lower() or "placeholder" in prompt.lower()
        assert "commit" in prompt.lower()

    def test_mock_claude_returns_mock_script_command(self):
        """When mock_claude is provided, should return [mock_script, 'setup']."""
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt(
            "/tmp/docs/features/my-service",
            mock_claude="/path/to/mock-claude.sh"
        )

        assert cmd == ["/path/to/mock-claude.sh", "setup"]

    def test_mock_claude_none_returns_normal_command(self):
        """When mock_claude is None, should return normal Claude command."""
        from i2code.implement.implement import build_scaffolding_prompt

        cmd = build_scaffolding_prompt(
            "/tmp/docs/features/my-service",
            mock_claude=None
        )

        assert cmd[0] == "claude"


@pytest.mark.unit
class TestEnsureProjectSetup:
    """Test ensure_project_setup() orchestration."""

    def _make_claude_result(self, returncode=0):
        return ClaudeResult(returncode=returncode, stdout="", stderr="")

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_checks_out_integration_branch(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait
    ):
        """Should checkout integration branch before invoking Claude."""
        from i2code.implement.implement import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
        )

        mock_repo.git.checkout.assert_called_with("idea/test/integration")

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_interactive_calls_run_claude_interactive(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait
    ):
        """Interactive mode should use run_claude_interactive."""
        from i2code.implement.implement import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=True,
        )

        mock_run_claude.assert_called_once_with(["claude", "prompt"], cwd="/tmp/fake-repo")

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_with_output_capture")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_non_interactive_calls_output_capture(
        self, mock_build_prompt, mock_run_capture, mock_push, mock_wait
    ):
        """Non-interactive mode should use run_claude_with_output_capture."""
        from i2code.implement.implement import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "-p", "prompt"]
        mock_run_capture.return_value = self._make_claude_result()

        ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=False,
        )

        mock_run_capture.assert_called_once_with(["claude", "-p", "prompt"], cwd="/tmp/fake-repo")

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_no_new_commits_skips_push_and_ci(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait
    ):
        """When Claude makes no commits, should skip push and CI, return True."""
        from i2code.implement.implement import ensure_project_setup

        mock_repo = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        # HEAD stays the same before and after Claude
        mock_repo.head.commit = mock_commit
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
        )

        assert result is True
        mock_push.assert_not_called()
        mock_wait.assert_not_called()

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_push_and_ci_when_commits_made(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait
    ):
        """When Claude makes commits, should push and wait for CI."""
        from i2code.implement.implement import ensure_project_setup

        mock_repo = MagicMock()
        # HEAD advances after Claude invocation
        commit_before = MagicMock()
        commit_before.hexsha = "aaa111"
        commit_after = MagicMock()
        commit_after.hexsha = "bbb222"
        type(mock_repo.head).commit = PropertyMock(side_effect=[commit_before, commit_after])
        mock_repo.working_tree_dir = "/tmp/fake-repo"

        mock_build_prompt.return_value = ["claude", "prompt"]
        mock_run_claude.return_value = self._make_claude_result()
        mock_push.return_value = True
        mock_wait.return_value = (True, None)  # CI passes

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            ci_timeout=300,
        )

        assert result is True
        mock_push.assert_called_once_with("idea/test/integration")
        mock_wait.assert_called_once_with("idea/test/integration", "bbb222", timeout_seconds=300)

    @patch("i2code.implement.implement.fix_ci_failure")
    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_with_output_capture")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_ci_failure_retry_success(
        self, mock_build_prompt, mock_run_capture, mock_push, mock_wait, mock_fix_ci
    ):
        """When CI fails, should invoke fix_ci_failure and return its result."""
        from i2code.implement.implement import ensure_project_setup

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
        mock_wait.return_value = (False, {"name": "CI", "id": 123})  # CI fails
        mock_fix_ci.return_value = True  # fix succeeds

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            interactive=False,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
        )

        assert result is True
        mock_fix_ci.assert_called_once_with(
            "idea/test/integration",
            "bbb222",
            "/tmp/fake-repo",
            max_retries=5,
            interactive=False,
            mock_claude="/mock.sh",
        )

    @patch("i2code.implement.implement.fix_ci_failure")
    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_ci_failure_retry_fails(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait, mock_fix_ci
    ):
        """When CI fails and fix_ci_failure also fails, should return False."""
        from i2code.implement.implement import ensure_project_setup

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
        mock_wait.return_value = (False, {"name": "CI", "id": 123})
        mock_fix_ci.return_value = False  # fix fails

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
        )

        assert result is False

    @patch("i2code.implement.implement.wait_for_workflow_completion")
    @patch("i2code.implement.implement.push_branch_to_remote")
    @patch("i2code.implement.implement.run_claude_interactive")
    @patch("i2code.implement.implement.build_scaffolding_prompt")
    def test_ensure_project_setup_skip_ci_wait_pushes_but_no_wait(
        self, mock_build_prompt, mock_run_claude, mock_push, mock_wait
    ):
        """When skip_ci_wait=True and commits made, should push but not wait for CI."""
        from i2code.implement.implement import ensure_project_setup

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

        result = ensure_project_setup(
            repo=mock_repo,
            idea_directory="/tmp/idea",
            idea_name="test",
            integration_branch="idea/test/integration",
            skip_ci_wait=True,
        )

        assert result is True
        mock_push.assert_called_once_with("idea/test/integration")
        mock_wait.assert_not_called()


@pytest.mark.unit
class TestCLIIsolateProjectSetup:
    """Test --isolate CLI path calls ensure_project_setup before delegating."""

    @patch("i2code.implement.cli.subprocess")
    @patch("i2code.implement.cli.ensure_project_setup", return_value=True)
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_cli_isolate_calls_setup_before_delegation(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_setup, mock_subprocess
    ):
        """--isolate should call ensure_project_setup before delegating to isolarium."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolate"])

        mock_ensure_branch.assert_called_once()
        mock_ensure_setup.assert_called_once()
        # Isolarium should have been delegated to (subprocess.run called)
        mock_subprocess.run.assert_called_once()

    @patch("i2code.implement.cli.subprocess")
    @patch("i2code.implement.cli.ensure_project_setup", return_value=False)
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_cli_isolate_exits_on_setup_failure(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_setup, mock_subprocess
    ):
        """--isolate should exit with error when ensure_project_setup fails."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolate"])

        assert result.exit_code != 0
        mock_subprocess.run.assert_not_called()

    @patch("i2code.implement.cli.subprocess")
    @patch("i2code.implement.cli.ensure_project_setup", return_value=True)
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_cli_isolate_forwards_parameters_to_setup(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_setup, mock_subprocess
    ):
        """--isolate should forward all relevant parameters to ensure_project_setup."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(implement_cmd, [
            "/tmp/fake-idea", "--isolate",
            "--non-interactive",
            "--mock-claude", "/mock.sh",
            "--ci-fix-retries", "5",
            "--ci-timeout", "900",
            "--skip-ci-wait",
        ])

        mock_ensure_setup.assert_called_once_with(
            repo=mock_repo,
            idea_directory="/tmp/fake-idea",
            idea_name="test-feature",
            integration_branch="idea/test-feature/integration",
            interactive=False,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            ci_timeout=900,
            skip_ci_wait=True,
        )

    @patch("i2code.implement.cli.subprocess")
    @patch("i2code.implement.cli.ensure_project_setup", return_value=True)
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_non_interactive_isolate_passes_interactive_false(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_setup, mock_subprocess
    ):
        """--isolate --non-interactive should pass interactive=False to ensure_project_setup."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolate", "--non-interactive"])

        call_kwargs = mock_ensure_setup.call_args[1]
        assert call_kwargs["interactive"] is False

    @patch("i2code.implement.cli.subprocess")
    @patch("i2code.implement.cli.ensure_project_setup", return_value=True)
    @patch("i2code.implement.cli.ensure_integration_branch", return_value="idea/test-feature/integration")
    @patch("i2code.implement.cli.validate_idea_files")
    @patch("i2code.implement.cli.validate_idea_files_committed")
    @patch("i2code.implement.cli.validate_idea_directory", return_value="test-feature")
    @patch("i2code.implement.cli.Repo")
    def test_interactive_isolate_passes_interactive_true(
        self, mock_repo_cls, mock_validate_dir, mock_validate_committed,
        mock_validate_files, mock_ensure_branch, mock_ensure_setup, mock_subprocess
    ):
        """--isolate without --non-interactive should pass interactive=True."""
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_repo = MagicMock()
        mock_repo.working_tree_dir = "/tmp/fake-repo"
        mock_repo_cls.return_value = mock_repo
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(implement_cmd, ["/tmp/fake-idea", "--isolate"])

        call_kwargs = mock_ensure_setup.call_args[1]
        assert call_kwargs["interactive"] is True
