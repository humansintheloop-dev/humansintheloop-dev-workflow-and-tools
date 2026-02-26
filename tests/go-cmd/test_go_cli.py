"""CLI integration tests for the go command."""

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestGoCommandRegistered:
    def test_go_command_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["go", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_go_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["go"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestGoCommandInvokesOrchestrator:
    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_invokes_orchestrator_for_existing_directory(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        runner = CliRunner()
        result = runner.invoke(main, ["go", str(tmp_path)])

        assert result.exit_code == 0
        mock_orch_cls.assert_called_once()
        mock_orch.run.assert_called_once()

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_constructs_idea_project_with_directory(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        runner = CliRunner()
        result = runner.invoke(main, ["go", str(tmp_path)])

        assert result.exit_code == 0
        call_args = mock_orch_cls.call_args
        project = call_args[0][0]
        assert project.directory == str(tmp_path)


@pytest.mark.unit
class TestGoCommandBanner:
    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_displays_banner_with_project_name(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        idea_dir = tmp_path / "my-project"
        idea_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["go", str(idea_dir)])

        assert "my-project" in result.output
        assert str(idea_dir) in result.output

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_displays_banner_header(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        runner = CliRunner()
        result = runner.invoke(main, ["go", str(tmp_path)])

        assert "Idea-to-Code Workflow Orchestrator" in result.output


@pytest.mark.unit
class TestGoCommandDirectoryCreation:
    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_prompts_to_create_nonexistent_directory(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        nonexistent = str(tmp_path / "new-project")
        runner = CliRunner()
        result = runner.invoke(main, ["go", nonexistent], input="y\n")

        assert result.exit_code == 0
        assert os.path.isdir(nonexistent)
        mock_orch.run.assert_called_once()

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_exits_when_user_declines_directory_creation(self, mock_orch_cls, tmp_path):
        nonexistent = str(tmp_path / "new-project")
        runner = CliRunner()
        result = runner.invoke(main, ["go", nonexistent], input="n\n")

        assert result.exit_code == 1
        assert not os.path.isdir(nonexistent)
        mock_orch_cls.assert_not_called()

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_directory_creation_message(self, mock_orch_cls, tmp_path):
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        nonexistent = str(tmp_path / "new-project")
        runner = CliRunner()
        result = runner.invoke(main, ["go", nonexistent], input="y\n")

        assert "does not exist" in result.output.lower()
        assert "create" in result.output.lower()
