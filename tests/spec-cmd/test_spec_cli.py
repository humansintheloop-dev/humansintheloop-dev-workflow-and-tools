"""CLI integration tests for i2code spec create and i2code spec revise."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


SPEC_COMMANDS = [
    ("create", "i2code.spec_cmd.cli.create_spec"),
    ("revise", "i2code.spec_cmd.cli.revise_spec"),
]


@pytest.mark.unit
class TestSpecCreateCommandRegistered:

    def test_spec_create_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "create", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_spec_create_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "create"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestSpecReviseCommandRegistered:

    def test_spec_revise_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "revise", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_spec_revise_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "revise"])
        assert result.exit_code != 0


def invoke_spec_command(mock_target, subcommand, tmp_path):
    """Invoke a spec subcommand with mocked spec function and ClaudeRunner.

    Returns (result, mock_spec_fn, mock_runner) where mock_runner is the
    ClaudeRunner instance passed to the spec function.
    """
    with patch(mock_target) as mock_spec_fn, \
         patch("i2code.spec_cmd.cli.ClaudeRunner") as mock_runner_cls:
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        mock_spec_fn.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", subcommand, str(tmp_path)])
        return result, mock_spec_fn, mock_runner


@pytest.mark.unit
@pytest.mark.parametrize("subcommand,mock_target", SPEC_COMMANDS)
class TestSpecCommandInvokesSpecFunction:

    def test_invokes_spec_function_for_existing_directory(
        self, subcommand, mock_target, tmp_path,
    ):
        result, mock_spec_fn, _ = invoke_spec_command(
            mock_target, subcommand, tmp_path,
        )
        assert result.exit_code == 0
        mock_spec_fn.assert_called_once()

    def test_constructs_idea_project_with_directory(
        self, subcommand, mock_target, tmp_path,
    ):
        result, mock_spec_fn, _ = invoke_spec_command(
            mock_target, subcommand, tmp_path,
        )
        assert result.exit_code == 0
        project = mock_spec_fn.call_args[0][0]
        assert project.directory == str(tmp_path)

    def test_passes_claude_runner_instance(
        self, subcommand, mock_target, tmp_path,
    ):
        result, mock_spec_fn, mock_runner = invoke_spec_command(
            mock_target, subcommand, tmp_path,
        )
        assert result.exit_code == 0
        assert mock_spec_fn.call_args[0][1] is mock_runner
