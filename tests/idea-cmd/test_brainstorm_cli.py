"""CLI integration tests for i2code idea brainstorm."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestBrainstormCommandRegistered:

    def test_brainstorm_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["idea", "brainstorm", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_brainstorm_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["idea", "brainstorm"])
        assert result.exit_code != 0


def invoke_brainstorm(tmp_path):
    """Invoke brainstorm with mocked brainstorm_idea and ClaudeRunner.

    Returns (result, mock_brainstorm_fn, mock_runner).
    """
    with patch("i2code.idea_cmd.cli.brainstorm_idea") as mock_brainstorm, \
         patch("i2code.idea_cmd.cli.ClaudeRunner") as mock_runner_cls:
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        mock_brainstorm.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["idea", "brainstorm", str(tmp_path)])
        return result, mock_brainstorm, mock_runner


@pytest.mark.unit
class TestBrainstormCommandInvokesFunction:

    def test_invokes_brainstorm_idea_for_existing_directory(self, tmp_path):
        result, mock_brainstorm, _ = invoke_brainstorm(tmp_path)
        assert result.exit_code == 0
        mock_brainstorm.assert_called_once()

    def test_constructs_idea_project_with_directory(self, tmp_path):
        result, mock_brainstorm, _ = invoke_brainstorm(tmp_path)
        assert result.exit_code == 0
        project = mock_brainstorm.call_args[0][0]
        assert project.directory == str(tmp_path)

    def test_passes_claude_runner_instance(self, tmp_path):
        result, mock_brainstorm, mock_runner = invoke_brainstorm(tmp_path)
        assert result.exit_code == 0
        assert mock_brainstorm.call_args[0][1] is mock_runner
