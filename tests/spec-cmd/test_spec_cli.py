"""CLI integration tests for i2code spec create and i2code spec revise."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


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
class TestSpecCreateInvokesCreateSpec:

    @patch("i2code.spec_cmd.cli.create_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_invokes_create_spec_for_existing_directory(
        self, mock_runner_cls, mock_create_spec, tmp_path,
    ):
        mock_create_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "create", str(tmp_path)])

        assert result.exit_code == 0
        mock_create_spec.assert_called_once()

    @patch("i2code.spec_cmd.cli.create_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_constructs_idea_project_with_directory(
        self, mock_runner_cls, mock_create_spec, tmp_path,
    ):
        mock_create_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "create", str(tmp_path)])

        assert result.exit_code == 0
        call_args = mock_create_spec.call_args
        project = call_args[0][0]
        assert project.directory == str(tmp_path)

    @patch("i2code.spec_cmd.cli.create_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_passes_claude_runner_instance(
        self, mock_runner_cls, mock_create_spec, tmp_path,
    ):
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        mock_create_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "create", str(tmp_path)])

        assert result.exit_code == 0
        call_args = mock_create_spec.call_args
        assert call_args[0][1] is mock_runner


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


@pytest.mark.unit
class TestSpecReviseInvokesReviseSpec:

    @patch("i2code.spec_cmd.cli.revise_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_invokes_revise_spec_for_existing_directory(
        self, mock_runner_cls, mock_revise_spec, tmp_path,
    ):
        mock_revise_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "revise", str(tmp_path)])

        assert result.exit_code == 0
        mock_revise_spec.assert_called_once()

    @patch("i2code.spec_cmd.cli.revise_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_constructs_idea_project_with_directory(
        self, mock_runner_cls, mock_revise_spec, tmp_path,
    ):
        mock_revise_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "revise", str(tmp_path)])

        assert result.exit_code == 0
        call_args = mock_revise_spec.call_args
        project = call_args[0][0]
        assert project.directory == str(tmp_path)

    @patch("i2code.spec_cmd.cli.revise_spec")
    @patch("i2code.spec_cmd.cli.ClaudeRunner")
    def test_passes_claude_runner_instance(
        self, mock_runner_cls, mock_revise_spec, tmp_path,
    ):
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        mock_revise_spec.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        result = runner.invoke(main, ["spec", "revise", str(tmp_path)])

        assert result.exit_code == 0
        call_args = mock_revise_spec.call_args
        assert call_args[0][1] is mock_runner
